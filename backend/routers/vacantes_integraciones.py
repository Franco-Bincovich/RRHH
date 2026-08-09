"""
Escrituras del módulo de vacantes que van a una INTEGRACIÓN EXTERNA: publicar en LinkedIn (vía
Zernio) y revisar la casilla del sistema para ingerir CVs (vía Gmail).

Separado de `vacantes_escrituras.py`, que estaba en 79/80 —el techo nuevo del módulo después de
que el corte anterior liberara `vacantes.py`— y no admitía los endpoints del CV screening. Se
monta en el MISMO prefijo, así que las rutas no cambian. Molde: `areas_escrituras.py`,
`usuarios_escrituras.py`.

POR QUÉ SALIERON ESTOS DOS Y NO OTROS: el corte no es por conteo, es la costura que el propio
docstring de `vacantes_escrituras.py` ya describía. Los dos son las únicas escrituras del módulo
que **NO pasan por `VacanteService`**: llaman directo a `ZernioService` y `GmailService`, que
resuelven la vacante y su empresa por su cuenta. El resto son el CRUD de la vacante y el alta
manual de un candidato, que sí van por el service. Y es donde crece el CV screening: la lectura
de la casilla, el matcheo del código y la bajada del CV son todos endpoints de integración.

🔴 NINGUNO DE LOS DOS LLEVA DECORADOR DE RATE LIMIT, y por eso se los pudo mover. La clave del
limiter es `routers.<módulo>.<función>`: mudar de archivo un endpoint decorado le cambia la clave
y le resetea el contador en silencio. Verificado antes de mover que el módulo entero está bajo el
baseline por middleware (300/min), sin un solo `@limiter` — el único decorado del módulo es
`exportar_vacantes`, que vive en `vacantes.py` y no se tocó.

El gate de permisos viaja con cada endpoint: los dos siguen exigiendo `VACANTES + WRITE`.
El orden de registro respecto de los otros dos routers del prefijo no es load-bearing.

⚠️ `POST /{id}/candidatos-desde-email` SE BORRÓ el 9/8/2026. Era el alta de a uno del botón
viejo, que `POST /casilla/revisar` reemplaza: aquel listaba con `format=metadata` —que ni
siquiera trae los adjuntos— y decidía qué era una postulación con un filtro por palabras clave
que descartaba en silencio mails con código. No conviven dos criterios sobre la misma casilla.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from schemas.cv_ingesta import AsignacionResponse, AsignarMailRequest, IngestaResponse, MailPendienteItem
from schemas.vacante import PublicarLinkedinRequest, PublicarLinkedinResponse
from services.cv_ingesta_service import CvIngestaService
from services.cv_pendientes_service import CvPendientesService
from services.zernio_service import ZernioService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.VACANTES


@router.post("/{id}/publicar-linkedin", response_model=PublicarLinkedinResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def publicar_linkedin(id: UUID, body: PublicarLinkedinRequest, request: Request) -> PublicarLinkedinResponse:
    return ZernioService().publicar_en_vacante(str(id), body.email_contacto, request.state.user["id"], get_empresa_id(request))


# 🔴 NO lleva `{id}`: la corrida es sobre la CASILLA entera, no sobre una vacante. Cada mail
# elige su vacante por el código del asunto, y una corrida puede tocar varias — incluso de
# empresas distintas. Colgarlo de una vacante habría obligado a elegir una antes de saber cuáles
# hacen falta. Por eso tampoco usa `get_empresa_id`.
# Va ANTES de nada con `{id}` no por orden de match (el path es literal y no colisiona) sino
# porque es el endpoint principal del módulo.
@router.post("/casilla/revisar", response_model=IngestaResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def revisar_casilla(request: Request) -> IngestaResponse:
    """Lee la casilla del sistema, matchea por código y crea los candidatos con su CV."""
    return CvIngestaService().revisar_casilla(request.state.user.get("id"))


# Los pendientes NO se persisten: se releen de la casilla. Por eso es un GET sin filtros — el
# estado es el buzón. Ver services/_cv_pendientes.py.
@router.get("/casilla/pendientes", response_model=List[MailPendienteItem], dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def casilla_pendientes(request: Request) -> List[MailPendienteItem]:
    """Mails con adjunto que no matchearon ninguna vacante y todavía no generaron candidatos."""
    return CvPendientesService().pendientes()


@router.post("/casilla/asignar", response_model=AsignacionResponse, dependencies=[Depends(require_permission(SECCION, Accion.WRITE))])
async def casilla_asignar(body: AsignarMailRequest, request: Request) -> AsignacionResponse:
    """Crea los candidatos de un mail sobre la vacante que eligió RRHH."""
    return CvPendientesService().asignar_mail(
        body.message_id, body.vacante_id, get_empresa_id(request), request.state.user.get("id"))
