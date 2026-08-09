"""
"Revisar la casilla": la corrida completa de ingesta de CVs. Fase 5 del flujo.

    listar mails con adjunto → por cada uno: matchear el código, bajar los CVs, crear candidatos

## 🔴 ES UN BOTÓN, NO UN PROCESO AUTOMÁTICO — y no solo por Vercel

Vercel no corre nada periódico, pero el motivo de fondo es otro: con 0 candidatos históricos
nadie sabe todavía cuál es la cadencia correcta. **Un botón la revela** —si RRHH lo aprieta 8
veces por día, ahí está el dato para automatizarlo— y además tiene dueño: un cron que falla a las
3am no lo mira nadie. El día que se automatice, esto se llama desde otro lado sin tocar una línea:
por eso la corrida no depende de ningún `user_id` (el token sale de la casilla del sistema) y el
`usuario_id` es opcional, solo para el evento de auditoría.

## 🔴 PRESUPUESTO DE TIEMPO: SON 2+ LLAMADAS A GMAIL POR CV

Traer el mensaje es una llamada y bajar cada adjunto es otra, así que 20 mails con un CV cada uno
son 40+ round-trips más las escrituras a Storage. `vercel.json` corta a los 300 s **sin reporte y
sin decir cuál mitad quedó hecha**. Con presupuesto, se chequea el margen ANTES de cada mail y al
agotarse se devuelve lo procesado y cuántos quedaron. La idempotencia hace el resto: reintentar
saltea los CVs que ya entraron, así que un lote cortado se completa apretando de nuevo.

⚠️ El presupuesto es MÁS CHICO que el techo de la plataforma a propósito: hay que dejar lugar
para que la respuesta viaje. Ver `services/_presupuesto.py`.

## 🔴 UN EVENTO DE AUDITORÍA POR LOTE, NUNCA UNO POR CV

Regla propia del repo para importaciones. Una corrida es UNA acción de RRHH; emitir un evento por
candidato convertiría un click en 40 filas de `auditoria` y haría ilegible la pantalla. Molde:
`payload_importacion_costos`. El `registro_id` es un uuid4 de EVENTO, no de recurso: una corrida
no persiste ninguna fila con id propio.
"""
from typing import List, Optional
from uuid import uuid4

from repositories.candidato_repo import CandidatoRepo
from repositories.vacante_repo import VacanteRepo
from schemas.cv_ingesta import IngestaMailItem, IngestaResponse
from services._cv_ingesta_mail import procesar_mail
from services._presupuesto import Presupuesto
from services.audit_service import AuditService
from services.cv_service import CvService
from services.gmail_service import GmailService, cliente_o
from utils.logger import logger

# Segundos para la corrida entera. Por debajo del `maxDuration: 300` de vercel.json, con margen
# para que la respuesta salga. No es settings: subirlo exige revisar el techo de la plataforma,
# y eso es una decisión, no configuración. Mismo criterio que LIMITE_FILAS_EXPORT.
PRESUPUESTO_SEGUNDOS = 240.0


class CvIngestaService:
    def __init__(self, gmail=None, vacante_repo=None, candidato_repo=None,
                 cv_service=None, audit=None) -> None:
        self._gmail = gmail or GmailService()
        self._vacantes = vacante_repo or VacanteRepo()
        self._candidatos = candidato_repo or CandidatoRepo()
        self._cv = cv_service or CvService()
        self._audit = audit or AuditService()

    def revisar_casilla(self, usuario_id: Optional[str] = None,
                        presupuesto: Optional[float] = None,
                        cliente=None) -> IngestaResponse:
        """Procesa la casilla del sistema y devuelve el resumen de la corrida.

        Raises:
            AppError: GMAIL_SIN_CASILLA (400) si no hay casilla designada · GMAIL_ERROR (502) si
                falla el LISTADO. Un mail suelto que falle NO corta la corrida: vuelve como
                pendiente con `motivo="error"`.
        """
        token = self._gmail.token()
        reloj = Presupuesto(PRESUPUESTO_SEGUNDOS if presupuesto is None else presupuesto)
        with cliente_o(cliente) as cli:
            ids = self._gmail.ids_con_adjunto(cli, token)
            items = [self._uno(cli, token, mid) for mid in reloj.con_margen(ids)]
        return self._resumen(items, reloj, len(ids), usuario_id)

    def _uno(self, cliente, token: str, message_id: str) -> IngestaMailItem:
        """Un mail. Cualquier fallo suyo queda contenido acá: el lote sigue."""
        try:
            mensaje = self._gmail.mensaje_completo(cliente, token, message_id)
            r = procesar_mail(cliente, token, mensaje, vacante_repo=self._vacantes,
                              candidato_repo=self._candidatos, cv_service=self._cv)
        except Exception as exc:  # noqa: BLE001 — ver el docstring
            logger.error("Fallo al procesar un mail de la casilla",
                         extra={"message_id": message_id, "error": str(exc)})
            return IngestaMailItem(message_id=message_id, motivo="error", pendiente=True)
        return IngestaMailItem(
            message_id=r.message_id, asunto=r.asunto, remitente=r.remitente, codigo=r.codigo,
            candidatos_creados=len(r.candidatos_creados), ya_existian=r.ya_existian,
            descartados=r.descartados, motivo=r.motivo, pendiente=r.pendiente)

    def _resumen(self, items: List[IngestaMailItem], reloj: Presupuesto, total: int,
                 usuario_id: Optional[str]) -> IngestaResponse:
        creados = sum(i.candidatos_creados for i in items)
        respuesta = IngestaResponse(
            mails_leidos=len(items), candidatos_creados=creados,
            ya_existian=sum(i.ya_existian for i in items),
            pendientes=[i for i in items if i.pendiente],
            parcial=reloj.parcial, sin_procesar=reloj.sin_procesar,
            segundos=reloj.transcurridos())
        self._audit.registrar(
            usuario_id=usuario_id, entidad="candidato", registro_id=str(uuid4()),
            accion="INSERT", evento="ingesta_cv_gmail",
            # 🔴 empresa_id=None: una corrida puede crear candidatos de VARIAS empresas (la de
            # cada vacante matcheada). Poner una sola sería afirmar algo falso; es el mismo
            # criterio que `payload_importacion_nomina`, no el de costos.
            empresa_id=None, datos_anteriores=None,
            datos_nuevos={"mails_con_adjunto": total, "mails_leidos": len(items),
                          "candidatos_creados": creados,
                          "ya_existian": respuesta.ya_existian,
                          "pendientes": len(respuesta.pendientes),
                          "parcial": reloj.parcial, "sin_procesar": reloj.sin_procesar})
        logger.info("Ingesta de CVs terminada",
                    extra={"creados": creados, "pendientes": len(respuesta.pendientes)})
        return respuesta
