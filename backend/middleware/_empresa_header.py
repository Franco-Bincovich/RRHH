"""
Resolución del header `X-Empresa-Id` a un empresa_id de verdad.

Salió de `middleware/auth.py`, que quedó en 209 líneas contra un límite de 200 al sumarle los
cortes por estado de usuario. Es el bloque que menos tenía que ver con el resto de ese archivo:
no comparte ni imports, ni estado, ni flujo con la verificación del JWT — `dispatch` lo llama
una vez, con un string, y recibe otro. Lo único que tienen en común es correr en el mismo
request.
"""
from typing import Optional
from uuid import UUID

from utils.empresas_cache import empresa_existe
from utils.logger import logger


def resolver_empresa_id(header: str, path: str) -> Optional[str]:
    """Resuelve el empresa_id del request a partir del header X-Empresa-Id.

    None significa "todas las empresas" (vista consolidada) y es el resultado de TRES casos que
    a propósito se tratan igual: header ausente, header "todas", y header que no supera la
    validación. Antes solo se validaba el FORMATO, así que un UUID sintácticamente correcto de
    una empresa inexistente entraba igual y viajaba aguas abajo: los listados salían vacíos,
    pero además ese id llegaba a columnas con FK a `empresas` —`auditoria.empresa_id` entre
    ellas— y hacía fallar el INSERT del evento de auditoría, que AuditService se traga por
    diseño. La operación de negocio se completaba y el registro desaparecía sin rastro.

    Un id inexistente se DESCARTA en silencio, sin status propio: no hace falta uno. Un UUID
    falso apunta a menos que None (que es la vista más amplia), así que no es escalación de
    privilegios y un 400 no compraría seguridad — solo agregaría el oráculo de enumeración de
    empresas que la Fase 2 se ocupó de cerrar. Sí se loguea a WARNING: un UUID bien formado que
    no existe no sale del uso normal del producto.

    La existencia se consulta contra un caché por proceso, no contra la base (ver
    utils/empresas_cache.py, que además explica por qué es fail-open).

    Args:
        header: Valor crudo de X-Empresa-Id, ya sin espacios.
        path: Ruta del request, solo para trazabilidad en el log.

    Returns:
        El UUID en texto si es una empresa real; None en cualquier otro caso.
    """
    if not header or header == "todas":
        return None
    try:
        UUID(header)
    except ValueError:
        return None
    if empresa_existe(header):
        return header
    logger.warning(
        "X-Empresa-Id descartado: la empresa no existe",
        extra={"path": path, "empresa_id": header},
    )
    return None
