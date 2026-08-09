"""
Router del clasificador de CVs: el botón de la corrida y la corrección manual.

Router PROPIO y no endpoints colgados de los existentes: `vacantes.py` está en **80/80 exacto**
y `candidatos.py` también — la regla del repo es dividir ANTES de escribir, no correr el límite.

Los endpoints del CRITERIO se fueron a `routers/screening_criterio.py` cuando entró la corrección
manual: este archivo estaba en 75/80 y el endpoint nuevo no entraba. El corte quedó por
naturaleza, no por tamaño — acá viven las ACCIONES sobre candidatos (`Seccion.CANDIDATOS`) y
allá la CONFIGURACIÓN por empresa (`Seccion.CONFIGURACION`). Las URLs no cambiaron.

⏱️ El botón lleva rate limit propio de 20/hora: cada corrida son N llamadas a Claude y **cada
una cuesta plata**. Mismo criterio y mismo número que `POST /reportes/generar`, que es el otro
endpoint del repo que gasta tokens. La corrección manual NO lo lleva: no gasta tokens, y limitar
a un humano que revisa candidatos de a uno sería castigar justo el uso que el módulo pide.

🔴 Barrera de empresa: los dos endpoints reciben un id de recurso de afuera y los dos la validan
en el service (404 idéntico al de "no existe" — nunca un 403, que confirmaría que el recurso
ajeno existe).
"""
from fastapi import APIRouter, Depends, Request

from schemas.screening import ClasificacionUpdate, ScreeningLoteResponse
from schemas.vacante import CandidatoResponse
from services.cv_screening_service import CvScreeningService
from services.screening_correccion_service import ScreeningCorreccionService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission
from utils.rate_limit import limiter

router = APIRouter()

_CAND_WRITE = Depends(require_permission(Seccion.CANDIDATOS, Accion.WRITE))


def _lote() -> CvScreeningService: return CvScreeningService()


def _correccion() -> ScreeningCorreccionService: return ScreeningCorreccionService()


@router.post("/vacantes/{vacante_id}", response_model=ScreeningLoteResponse,
             dependencies=[_CAND_WRITE])
@limiter.limit("20/hour")  # N llamadas a Claude por corrida: cada request cuesta plata
async def clasificar_pendientes(
    vacante_id: str, request: Request, service: CvScreeningService = Depends(_lote),
) -> ScreeningLoteResponse:
    """Clasifica los CVs de la vacante que todavía no tienen clasificación. Reintentable."""
    return service.clasificar_pendientes(vacante_id, get_empresa_id(request),
                                         request.state.user.get("id"))


@router.put("/candidatos/{candidato_id}/clasificacion", response_model=CandidatoResponse,
            dependencies=[_CAND_WRITE])
async def corregir_clasificacion(
    candidato_id: str, body: ClasificacionUpdate, request: Request,
    service: ScreeningCorreccionService = Depends(_correccion),
) -> CandidatoResponse:
    """Corrige a mano la clasificación de un candidato. Queda marcada como HUMANA."""
    return service.corregir(candidato_id, body, get_empresa_id(request),
                            request.state.user.get("id"))
