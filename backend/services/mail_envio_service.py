"""
Envío de mails a partir de una plantilla: individual y masivo.

Separado de `plantillas_service` (que edita y previsualiza) porque son dos responsabilidades y
juntas no entran en 150 líneas. Todo lo que sale del sistema pasa por `services.mailer`, que es
el punto único: acá no hay una sola línea que sepa de Gmail.

## 🔴 INDIVIDUAL SÍNCRONO, MASIVO CON PRESUPUESTO
Un mail son 1-3 s: meterlo en una cola sería infraestructura nueva para un problema que no
existe. Un lote de 50 son ~100 s y puede pasarse de los 300 s de Vercel, así que va con
presupuesto de tiempo y reporte parcial (`_lote_mails`, molde `LoteNomina`).

## 🔴 LA IDEMPOTENCIA ES LO QUE HACE CONTINUABLE EL REINTENTO
Antes de cada mail se consulta `mail_enviado.ya_enviado`. El peor caso no es que tarde: es mandar
30, morir en el timeout, y que el reintento mande esos 30 DE NUEVO — un daño visible para 30
personas de afuera. Con el chequeo, reintentar el mismo lote saltea lo que ya salió y termina lo
que falta, igual que el import de nómina se apoya en el dedup por DNI.

## Auditoría: UN evento por lote
Regla propia del repo ("al auditar una importación, un evento por lote"). Un envío a 50 personas
es UN evento con el conteo, no 50 — el detalle fila por fila ya vive en `mail_enviado`.
"""
from typing import List, Optional
from uuid import UUID, uuid4

from repositories.empleado_repo import EmpleadoRepo
from repositories.mail_enviado_repo import MailEnviadoRepo
from repositories.plantilla_mail_repo import PlantillaMailRepo
from schemas.plantillas import EnvioRequest, EnvioResponse
from services._envio_libre import enviar_a_direccion, validar
from services._lote_mails import LoteMails
from services.audit_service import AuditService
from services.mailer import enviar_mail
from services.mailer._render import render
from services.plantillas_service import datos_empleado
from utils.errors import AppError
from utils.logger import logger


class MailEnvioService:
    def __init__(self, plantillas: Optional[PlantillaMailRepo] = None,
                 empleados: Optional[EmpleadoRepo] = None,
                 log: Optional[MailEnviadoRepo] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._plantillas = plantillas or PlantillaMailRepo()
        self._empleados = empleados or EmpleadoRepo()
        self._log = log or MailEnviadoRepo()
        self._audit = audit or AuditService()

    def enviar(self, data: EnvioRequest, empresa_id: Optional[UUID],
               usuario_id: Optional[str], lote: Optional[LoteMails] = None) -> EnvioResponse:
        """Manda la plantilla a cada destinatario. Uno solo o cincuenta: el mismo camino.

        Dos modos, EXCLUYENTES entre sí (ver `EnvioRequest`): empleados del sistema, o direcciones
        escritas a mano. El segundo vive en `services/_envio_libre.py` — incluida la regla de que
        una plantilla con variables no se puede mandar a una dirección suelta.

        Args:
            data: clave de la plantilla y los destinatarios (empleados o direcciones).
            empresa_id: la del request; resuelve qué plantilla se usa (propia o global).
            usuario_id: quién disparó, para el log y la auditoría.
            lote: inyectable para test (reloj falso). None → presupuesto de settings.

        Raises:
            AppError: PLANTILLA_NOT_FOUND (404) si no hay plantilla con esa clave.
        """
        plantilla = self._plantillas.find(data.plantilla_clave, empresa_id)
        if not plantilla:
            raise AppError("Plantilla no encontrada", "PLANTILLA_NOT_FOUND", 404)
        if data.empleado_ids and data.destinatarios_libres:
            raise AppError(
                "Elegí empleados del sistema o direcciones escritas a mano, no las dos cosas en "
                "el mismo envío.", "ENVIO_MODO_MIXTO", 422)

        lote = lote or LoteMails()
        if data.destinatarios_libres:
            # Valida ANTES de mandar el primero: si una dirección está mal escrita, el lote entero
            # se rechaza y no queda medio mandado. Es distinto del camino de empleados, donde un
            # dato faltante de uno no puede castigar a los otros 49 — acá la lista la acaba de
            # escribir una persona y corregirla es inmediato.
            libres = validar(plantilla, list(data.destinatarios_libres))
            for direccion in lote.destinatarios_con_margen(libres):
                enviar_a_direccion(lote, plantilla, direccion, empresa_id, usuario_id, self._log)
        for empleado_id in lote.destinatarios_con_margen(list(data.empleado_ids)):
            self._uno(lote, plantilla, empleado_id, empresa_id, usuario_id)

        resumen = lote.resumen()
        self._audit.registrar(**_payload_lote(data.plantilla_clave, resumen, usuario_id, empresa_id))
        logger.info("Envío de mails", extra={"plantilla": data.plantilla_clave, **resumen})
        return EnvioResponse(**resumen)

    def _uno(self, lote: LoteMails, plantilla: dict, empleado_id, empresa_id, usuario_id) -> None:
        """Un destinatario. Best-effort: un fallo se anota y NO corta el lote.

        Los empleados ya existen y los demás mails son independientes: abortar todo porque uno no
        tiene email cargado sería castigar a los 49 restantes por un dato faltante de uno.
        """
        emp = self._empleados.find_by_id(str(empleado_id), empresa_id)
        if not emp or not emp.email_corporativo:
            lote.registrar_fallo(str(empleado_id), "el empleado no tiene email corporativo cargado")
            return
        if self._log.ya_enviado(plantilla["clave"], str(empleado_id)):
            lote.registrar_omitido()   # ← lo que hace continuable el reintento
            return
        datos = {"empresa": {"nombre": getattr(emp, "empresa_nombre", None)},
                 "empleado": datos_empleado(emp)}
        asunto, cuerpo, faltantes = render(plantilla["contexto"], plantilla["asunto"],
                                           plantilla["cuerpo"], datos)
        if faltantes:
            # No corta: una variable sin valor es un dato faltante, no un error (momento 2 de los
            # tres, ver `_render`). Queda el rastro para poder explicar un mail con un hueco.
            logger.warning("Mail con variables sin valor", extra={
                "empleado_id": str(empleado_id), "faltantes": faltantes})
        try:
            enviar_mail(emp.email_corporativo, asunto, cuerpo,
                        empresa_id=empresa_id, plantilla_clave=plantilla["clave"],
                        contexto=plantilla["contexto"], empleado_id=str(empleado_id),
                        enviado_por=usuario_id)
            lote.registrar_envio()
        except AppError as exc:
            lote.registrar_fallo(emp.email_corporativo, exc.message)


def _payload_lote(clave: str, resumen: dict, usuario_id, empresa_id) -> dict:
    """UN evento de auditoría por lote, con el conteo. El detalle vive en `mail_enviado`.

    `registro_id` es un uuid4 de EVENTO y no un id de recurso: un envío no persiste un lote con
    id propio. Mismo criterio (y mismo bug evitado) que `payload_importacion_nomina`, donde un
    literal en esa columna hacía fallar el insert y el evento desaparecía en silencio.
    """
    return {"usuario_id": usuario_id, "entidad": "mail", "registro_id": str(uuid4()),
            "accion": "INSERT", "evento": "envio_mails",
            "empresa_id": str(empresa_id) if empresa_id else None,
            "datos_anteriores": None,
            "datos_nuevos": {"plantilla": clave, "enviados": resumen["enviados"],
                             "omitidos": resumen["omitidos"],
                             "fallidos": len(resumen["fallidos"]),
                             "parcial": resumen["parcial"]}}


def destinatarios_pendientes(log: MailEnviadoRepo, clave: str,
                             empleado_ids: List[UUID]) -> List[UUID]:
    """Los que TODAVÍA no recibieron esta plantilla hoy. Para que la UI muestre qué queda.

    No lo usa el envío —que ya chequea uno por uno— sino la pantalla, para poder decir "quedan 12
    de 50" después de un corte parcial sin tener que reintentar a ciegas."""
    return [e for e in empleado_ids if not log.ya_enviado(clave, str(e))]
