"""
Handler global de errores. Todos los errores pasan por acá.
El cliente siempre recibe el mismo formato de respuesta de error.

DOS handlers, y el segundo delega en el primero a propósito:
  · `global_error_handler`     — AppError y todo lo inesperado.
  · `validation_error_handler` — el 422 de validación de FastAPI/Pydantic.

El 422 pasa por `global_error_handler` en vez de armar su propio JSONResponse por el MISMO
motivo que `rate_limit_handler` (utils/rate_limit.py): el contrato `{error, message, code}` lo
produce UNA sola función, así una respuesta de error no puede divergir del resto aunque el
formato cambie. Un body de error con otra forma es un bug esperando a que alguien lo parsee.
"""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from middleware._mensaje_validacion import mensaje_validacion
from utils.errors import AppError
from utils.logger import logger


async def global_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Captura todas las excepciones de la aplicación.
    AppError → log de warning con código y path.
    Cualquier otro error → log de error completo, sin exponer detalles al cliente.
    """
    if isinstance(exc, AppError):
        logger.warning(
            exc.message,
            extra={"code": exc.code, "path": str(request.url.path)},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.message,
                "code": exc.code,
            },
        )

    # Error inesperado — log completo pero sin exponer al cliente
    logger.error(
        "Error inesperado",
        extra={"error": str(exc), "path": str(request.url.path)},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Error interno del servidor. Intentá de nuevo en unos minutos.",
            "code": "INTERNAL_ERROR",
        },
    )


# ── 422 de validación ──────────────────────────────────────────────────────────
# El criterio de QUÉ se muestra y QUÉ solo se loguea vive en `_mensaje_validacion.py`, junto a la
# traducción que gobierna. Acá queda únicamente la forma de la respuesta.


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Devuelve el 422 de validación con el contrato del repo, no con el default de FastAPI.

    Sin este handler, FastAPI responde `{"detail": [...]}` con el volcado crudo de Pydantic: sin
    `message` y sin `code`. El front busca esas dos claves en UN solo lugar (`toApiError` de
    `services/api.ts`, embudo de `apiFetch`, `postMultipart` y `descargarArchivo`), no las
    encuentra y cae a "Error del servidor" con `code: "UNKNOWN"` — o sea que TODO 422 de TODA la
    app se muestra como un error del servidor, que además es mentira: un 422 es un problema del
    pedido, no del servidor. Ya pasó dos veces con `page_size=200` (`useDestinatarios` y
    `useCandidatosProyecto`), donde el 422 salía por pantalla como "no hay datos" con la base
    llena.

    El body lo arma `global_error_handler`; el criterio de qué se muestra y qué se loguea está
    en `_mensaje_validacion.py`.

    Args:
        request: Request rechazado.
        exc: La excepción de validación de FastAPI.

    Returns:
        Response 422 con `{error, message, code}`.
    """
    errores = exc.errors()
    logger.warning(
        "Validación de request rechazada",
        extra={
            "path": str(request.url.path),
            "metodo": request.method,
            "cantidad": len(errores),
            # `loc` y `type` alcanzan para diagnosticar. El `input` NO se loguea (ver criterio).
            "errores": [
                {"loc": ".".join(str(p) for p in e.get("loc", ())), "type": e.get("type", "")}
                for e in errores
            ],
        },
    )
    mensaje, code = mensaje_validacion(errores)
    return await global_error_handler(request, AppError(mensaje, code, 422))
