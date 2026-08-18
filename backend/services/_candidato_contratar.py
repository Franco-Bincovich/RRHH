"""
El puente candidato → empleado: la persona a la que se le hizo una oferta y la aceptó.

Es el tercer módulo del repo que registra **un ACTO con consecuencia y no la edición de un
campo**, y sigue el criterio de los otros dos: `_empleado_activar.py` (la persona entró) y
`_offboarding_efectivizar.py` (la persona se fue). Los tres tienen endpoint propio, guardas que
son la definición del acto, y ninguna escritura hasta que pasaron todas.

═══════════════════════════════════════════════════════════════════════════════════════════
LO QUE ESTE PUENTE NO HACE, A PROPÓSITO
═══════════════════════════════════════════════════════════════════════════════════════════

· **No toca `candidato.etapa`.** `oferta` es la última etapa del CHECK y ahí se queda: `etapa`
  dice DÓNDE llegó en el proceso y `estado` dice CÓMO terminó. Pisar la etapa perdería el dato
  de en qué punto se cerró cada búsqueda, que es la métrica del embudo.
· **No toca la vacante.** `cantidad_puestos` puede ser >1 y hoy no lo lee nadie, así que este
  módulo no puede saber si la búsqueda quedó cubierta. Cerrarla es decisión de RRHH y ya tiene
  camino propio (el PUT del estado de la vacante).
· **No crea ninguna referencia candidato→empleado.** La trazabilidad es DDL y está fuera de
  alcance por decisión tomada.
· **No reimplementa el alta.** Llama a `EmpleadoService.create_empleado`, así que hereda entero
  lo que ya está probado: legajo duplicado (409), área de otra empresa (404), manager inexistente
  (404), la traducción del 23505 a 409 por constraint (A4.1) y el evento `alta_empleado`.

📄 **LAS GUARDAS viven en `services/_candidato_contratar_guardas.py`**, con el porqué de cada
una — incluida la de fecha, que es la que explica por qué contratar exige `fecha_ingreso >= hoy`
mientras `POST /api/empleados/{id}/activar` exige lo contrario. Son dos endpoints que se
complementan: contratar registra un acuerdo hacia adelante, activar registra que la persona entró.

📄 **EL MAPEO DE CAMPOS vive en `services/_candidato_contratar_mapeo.py`**, junto con `_payload`,
que es el único que lo aplica. Ahí está de dónde sale cada uno de los doce campos y las dos
trampas que tiene: por qué `candidato.email` va a `email_personal` y NUNCA a `email_corporativo`
(UNIQUE GLOBAL), y por qué `tipo_contrato` no se copia de la vacante. Salió de acá cuando este
archivo llegó a 202/150, y el corte separa lo que CAMBIA —el mapeo, cada vez que aparece una
columna nueva en `empleados` o en `vacantes`— de lo que no: el acto y sus guardas.
🔑 **Las guardas se quedaron acá y allá no hay ninguna** (`_payload` no tiene un solo `raise`, y
hay un test estructural que lo fija). Validar es decidir si el acto procede, y eso es de este
archivo; armar el payload es traducir datos que ya se validaron.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 SIN TRANSACCIÓN — el límite conocido, declarado
═══════════════════════════════════════════════════════════════════════════════════════════
PostgREST no da transacciones. Si el paso 2 (marcar el candidato) falla después de que el paso 1
(crear el empleado) tuvo éxito, queda **el empleado creado y el candidato en `activo`**. Está
analizado en `docs/DEUDA-TECNICA.md` con qué pasa exactamente en el reintento. No se inventa una
compensación acá: borrar el empleado recién creado sería una segunda escritura que también puede
fallar, y dejaría el caso peor (un alta auditada y después borrada sin rastro del porqué).
"""
from typing import Optional
from uuid import UUID

from schemas.candidato import ContratarRequest
from schemas.empleado import EmpleadoResponse
from services._candidato_contratar_guardas import candidato_o_404 as _candidato_o_404
from services._candidato_contratar_guardas import validar as _validar
from services._candidato_contratar_mapeo import payload as _payload
from utils.errors import AppError
from utils.logger import logger

# El estado que este módulo ESCRIBE. Vive acá y no con las guardas a propósito: las de allá son
# los valores contra los que se COMPARA para decidir si el acto procede (`oferta`, `activo`), y
# éste es el resultado del acto. Se fue con ellas en el corte y `test_nombres_definidos` lo cazó
# como F821 — el barrido hizo exactamente lo que existe para hacer.
_ESTADO_CONTRATADO = "contratado"

def contratar(candidato_repo, vacante_repo, empleado_service, audit, candidato_id: str,
              data: ContratarRequest, empresa_id: Optional[UUID] = None,
              usuario_id: Optional[str] = None) -> EmpleadoResponse:
    """
    Convierte un candidato en oferta en un empleado en `preingreso`.

    🔴 SON DOS COMPROBACIONES DE EMPRESA DISTINTAS Y LAS DOS HACEN FALTA — molde exacto de
    `_candidato_acciones.asignar_vacante`: que el CANDIDATO sea alcanzable desde el header (el
    `.eq` del repo), y que la VACANTE se busque **con la empresa del CANDIDATO** y no con la del
    header. En modo consolidado el header vale `None` y no restringe nada, así que sin lo segundo
    se podría armar un empleado de Karstec con el área de una búsqueda de Dosuba.
    Por eso el ALTA también recibe la empresa del candidato, nunca la del header.

    Args:
        candidato_repo: CandidatoRepo (o doble de test).
        vacante_repo: VacanteRepo (o doble de test).
        empleado_service: EmpleadoService (o doble) — el alta NO se reimplementa acá.
        audit: AuditService (o doble de test).
        candidato_id: UUID (str) del candidato a contratar.
        data: los tres campos que no se pueden derivar (ver `ContratarRequest`).
        empresa_id: empresa activa del request. Acota A QUIÉN se puede apuntar (None = consolidado).
        usuario_id: operador, para la trazabilidad de auditoría.

    Returns:
        El empleado creado, en estado `preingreso`.

    Raises:
        AppError: CANDIDATO_NOT_FOUND (404) · CANDIDATO_SIN_VACANTE · CANDIDATO_NO_ESTA_EN_OFERTA ·
            CANDIDATO_NO_CONTRATABLE (409) · FECHA_INGRESO_PASADA (400) · VACANTE_NOT_FOUND (404).
            Más los del alta, que se heredan: LEGAJO_DUPLICADO / EMAIL_CORPORATIVO_DUPLICADO /
            DNI_DUPLICADO (409), AREA_NOT_FOUND / MANAGER_NOT_FOUND (404).
    """
    cand = _candidato_o_404(candidato_repo.find_by_id(candidato_id, empresa_id))
    _validar(cand, data.fecha_ingreso)
    empresa_cand = UUID(cand.empresa_id) if cand.empresa_id else None
    vacante = vacante_repo.find_by_id(cand.vacante_id, empresa_cand)
    if not vacante:
        raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)

    empleado = empleado_service.create_empleado(
        _payload(cand, vacante, data, empresa_cand), usuario_id or "system", empresa_cand)
    # 🔴 EL ESTADO ANTERIOR SE CAPTURA ANTES DE ESCRIBIR. `update_estado` puede devolver —o
    # mutar— la MISMA fila que `find_by_id` trajo, y en ese caso leer `cand.estado` después del
    # update daría "contratado → contratado": un evento de auditoría que no dice de dónde se
    # venía. Es el mismo motivo por el que `_vacante_candidatos.mover` lee `previo` antes.
    estado_previo = cand.estado
    candidato_repo.update_estado(candidato_id, _ESTADO_CONTRATADO, empresa_id)
    # La empresa del evento sale del CANDIDATO, no del header: auditar es una ACCIÓN y la empresa
    # sale de la entidad afectada (Vista vs Acción). Con el header, una contratación hecha en modo
    # consolidado grabaría el evento sin empresa. El alta emite su propio `alta_empleado`.
    audit.registrar(
        usuario_id=usuario_id, entidad="candidato", registro_id=candidato_id, accion="UPDATE",
        evento="contratacion_candidato", empresa_id=cand.empresa_id,
        datos_anteriores={"estado": estado_previo},
        datos_nuevos={"estado": _ESTADO_CONTRATADO, "empleado_id": empleado.id})
    logger.info("Candidato contratado",
                extra={"candidato_id": candidato_id, "empleado_id": empleado.id})
    return empleado
