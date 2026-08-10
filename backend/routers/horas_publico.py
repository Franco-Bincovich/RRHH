"""
Router PÚBLICO del link de carga de horas — IDENTIFICACIÓN Y LECTURAS.

Las dos ESCRITURAS (horas y licencia) viven en `routers/horas_publico_carga.py`, montado en el
MISMO prefijo: las rutas no cambian. El porqué del corte está en el docstring de ese archivo.

La identificación es la más débil de todas (solo dni, que es enumerable). TODO lo demás exige el
token de sesión de 256 bits con TTL que ella emite, así que la debilidad queda confinada a ese
primer paso. Antes de tocar esto: `services/identificacion_service.py` y `_sesion_horas.py`.

🔴 EL ROUTER SOLO SE MONTA CON `HORAS_PUBLICO_ENABLED`, y el MISMO flag gatea que las rutas
cuenten como públicas (middleware/_rutas_publicas.py). Las dos piezas, o el módulo se delata.

⚠️ EL RATE LIMIT QUEDA PUESTO AUNQUE EL FLAG ESTÉ APAGADO: encender el módulo no puede reabrir un
agujero cerrado. `request` lo exige slowapi para decorar.
"""
from fastapi import APIRouter, Depends, Query, Request

from schemas.horas_publico import (
    ClientesPublicosResponse, IdentificacionRequest, IdentificacionResponse, SemanaResponse,
)
from services.carga_horas_service import CargaHorasService
from services.identificacion_service import IdentificacionService
from utils.rate_limit import client_ip, limiter

router = APIRouter()


def _service() -> IdentificacionService:
    return IdentificacionService()


def _carga_service() -> CargaHorasService:
    return CargaHorasService()


# 10/min por IP, la franja de "público sin auth". 🔴 NO ES EL ÚNICO EJE: el segundo —20/hora POR
# DNI INTENTADO— vive en el service, y por qué hacen falta los dos está en `utils/rate_limit_dni`.
@router.post("/identificar", response_model=IdentificacionResponse)
@limiter.limit("10/minute")
async def identificar(
    request: Request,
    body: IdentificacionRequest,
    service: IdentificacionService = Depends(_service),
) -> IdentificacionResponse:
    # La IP se resuelve con `client_ip`, el mismo key_func del rate limit, y NO con
    # `request.client.host`: detrás de un proxy esa es la del edge, así que el log guardaría la
    # misma IP para todo el mundo y no serviría para ver una enumeración. Ver TRUSTED_PROXY_HOPS.
    return await service.identificar(
        body.dni, ip=client_ip(request), user_agent=request.headers.get("User-Agent"),
    )


# 10/min: es una LECTURA, así que va con la franja de "público sin auth" y no con la de 5/min de
# las escrituras. La simetría del repo es leer 10 / escribir 5 (assessment), y acá además la
# lectura no crea filas que después alguien tenga que revisar.
# 🔴 El token va en la QUERY y no en el body porque es un GET. Eso lo pone en la URL —y con ella
# en access logs e historial—, que es exactamente lo que se evitó con el dni. La diferencia: el
# token es rotable y vive 30 minutos, el dni es para siempre. Aun así es el punto más flojo de
# esta ruta, y por eso la ventana es de una semana y no un rango libre.
@router.get("/semana", response_model=SemanaResponse)
@limiter.limit("10/minute")
async def semana(
    request: Request,
    token: str = Query(..., min_length=1, max_length=128),
    service: CargaHorasService = Depends(_carga_service),
) -> SemanaResponse:
    return service.ver_semana(token)


# El catálogo del select. 10/min: es lectura, y además se pide UNA vez por sesión.
@router.get("/clientes", response_model=ClientesPublicosResponse)
@limiter.limit("10/minute")
async def clientes(
    request: Request,
    token: str = Query(..., min_length=1, max_length=128),
    service: CargaHorasService = Depends(_carga_service),
) -> ClientesPublicosResponse:
    return service.clientes_disponibles(token)
