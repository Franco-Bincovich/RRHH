"""
Las dos ESCRITURAS del link público de carga de horas: horas y licencia.

Separado de `routers/horas_publico.py` y montado en el MISMO prefijo, así que las rutas no
cambian. El corte es el patrón `*_escrituras.py` que el repo ya usa en areas, costos, objetivos
e inventario, con el mismo criterio que allá: **lo que motivó el corte es una LECTURA** (el GET
de la semana), así que las lecturas se quedan del lado que va a crecer y las escrituras salen.

Acá viven las dos operaciones que crean datos de negocio. `identificar` NO es una de ellas
aunque sea un POST: no escribe una carga, abre una sesión — es la puerta de entrada del flujo, y
por eso se queda con las lecturas.

🔴 Las dos exigen el TOKEN DE SESIÓN de 256 bits con TTL que emite el paso 1, así que —al revés
que la identificación— sí cumplen las condiciones #1 y #2 de las rutas públicas. La identidad
sale de la sesión, nunca del body: los schemas ni siquiera declaran `empleado_id`.
"""
from fastapi import APIRouter, Depends, Request

from routers.horas_publico import _carga_service
from schemas.horas_publico import (
    CargaHorasRequest, CargaHorasResponse, CargaLicenciaRequest, CargaLicenciaResponse,
)
from services.carga_horas_service import CargaHorasService
from utils.rate_limit import limiter

router = APIRouter()


# 🔴 LAS DOS ESCRITURAS VAN A 5/min, más restrictivas que la identificación (10/min): es la
# simetría de assessment (leer 10, escribir 5) más un motivo propio — estas ESCRIBEN, así que el
# costo del abuso son filas que después RRHH revisa a mano. El eje por DNI no se replica: acá no
# llega un DNI sino un token, ya acotado por su TTL y por el límite de quien lo emitió.
@router.post("/horas", response_model=CargaHorasResponse, status_code=201)
@limiter.limit("5/minute")
async def cargar_horas(
    request: Request,
    body: CargaHorasRequest,
    service: CargaHorasService = Depends(_carga_service),
) -> CargaHorasResponse:
    return service.cargar_horas(body)


@router.post("/licencia", response_model=CargaLicenciaResponse, status_code=201)
@limiter.limit("5/minute")
async def cargar_licencia(
    request: Request,
    body: CargaLicenciaRequest,
    service: CargaHorasService = Depends(_carga_service),
) -> CargaLicenciaResponse:
    return service.cargar_licencia(body)
