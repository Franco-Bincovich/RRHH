"""
Las tres escrituras del módulo de Áreas: alta, edición y baja.

Salió de `area_service.py`, que al sumarle los tres eventos de auditoría de la tanda del
25/8/2026 quedaba en 164 contra un tope de 150. Molde: `_objetivos_write.py`,
`_vacaciones_write.py` y `_costos_write.py` — funciones libres que reciben el repo y el
AuditService, sin estado ni `self`.

🔴 POR QUÉ SALIERON LAS TRES ESCRITURAS Y NO LAS LECTURAS, que son más largas.
`area_service.py` se queda con lo que tiene una decisión escrita encima: por qué `get_areas` NO
pagina (alimenta los ~15 selectores del front y un dropdown con 20 de 180 no da error, da un área
que "no existe") y por qué el `search` del export tiene que ser server-side (filtraba en el
cliente y el archivo salía con las 58 filas mostrando 3). Sacarlas dejaría al service sin lo único
que justifica leerlo. Estas tres, en cambio, no deciden nada: validan, escriben y auditan.

Los payloads viven en `services/_audit_payloads_areas.py`, con el porqué de cada campo — en
particular por qué la baja lleva `legajos_que_la_referenciaban`.
"""
from typing import Optional
from uuid import UUID

from schemas.area import AreaCreate, AreaResponse, AreaUpdate
from services._audit_payloads_areas import (
    payload_alta_area, payload_baja_area, payload_update_area,
)
from utils.errors import AppError
from utils.logger import logger

# El mismo literal para "no existe" y para "es de otra empresa" — barrera de empresa. Se repite
# en tres call sites de este archivo; un `area_or_404` sería una indirección para ahorrar dos
# líneas (mismo criterio que `_objetivos_write`).
_NO_ENCONTRADA = ("Área no encontrada", "AREA_NOT_FOUND", 404)


def crear(repo, audit, data: AreaCreate, created_by: Optional[str] = None) -> AreaResponse:
    """Crea un área nueva.

    Args:
        repo: AreaRepo (o doble).
        audit: AuditService (o doble).
        data: Datos del área (empresa_id + nombre requeridos).
        created_by: Operador, para la trazabilidad del evento.

    Returns:
        AreaResponse con los datos del área creada, incluyendo su ID generado.
    """
    area = repo.save(data)
    audit.registrar(**payload_alta_area(area, created_by))
    logger.info("Área creada", extra={"area_id": area.id, "created_by": created_by})
    return area


def actualizar(repo, audit, id: UUID, data: AreaUpdate, empresa_id: Optional[str] = None,
               usuario_id: Optional[str] = None) -> AreaResponse:
    """Edición parcial de un área (solo los campos no-None se aplican).

    🔑 EL `prior` SE LEE ANTES DE ESCRIBIR: sin él no hay diff que auditar. Es una query de más, y
    es el precio de que el log diga *qué cambió* en vez de *que algo cambió*. Leerlo DESPUÉS del
    update daría "nombre → nombre", que es el bug que `_candidato_contratar` documenta.

    Args:
        repo: AreaRepo (o doble).
        audit: AuditService (o doble).
        id: Área a editar.
        data: Campos a actualizar.
        empresa_id: Empresa del request. None = consolidado.
        usuario_id: Operador, para la trazabilidad del evento.

    Returns:
        AreaResponse con los datos actualizados.

    Raises:
        AppError: AREA_NOT_FOUND (404) si no existe o es de otra empresa.
    """
    prior = repo.find_by_id(str(id), empresa_id)
    if not prior:
        raise AppError(*_NO_ENCONTRADA)
    area = repo.update(str(id), data, empresa_id)
    if not area:
        raise AppError(*_NO_ENCONTRADA)
    audit.registrar(**payload_update_area(prior, area, usuario_id))
    logger.info("Área actualizada", extra={"area_id": str(id)})
    return area


def eliminar(repo, audit, id: UUID, empresa_id: Optional[str] = None,
             usuario_id: Optional[str] = None) -> bool:
    """Da de baja un área. La baja es LÓGICA (`activo=False`), no física.

    🔴 EL EVENTO SE ARMA CON LA FILA VIVA Y SE REGISTRA DESPUÉS DE LA BAJA. Antes, porque
    `cantidad_empleados` —los legajos que quedan apuntando al área— hay que leerlo mientras el
    área todavía figura en el catálogo activo (`find_by_id` filtra por `activo=True`, así que
    después de la baja devuelve None y no habría nada que fotografiar). Después, porque un evento
    emitido antes del update afirmaría una baja que todavía puede fallar. Mismo orden que
    `_objetivos_write.eliminar`.

    Args:
        repo: AreaRepo (o doble).
        audit: AuditService (o doble).
        id: Área a dar de baja.
        empresa_id: Empresa del request. None = consolidado.
        usuario_id: Operador, para la trazabilidad del evento.

    Returns:
        True si la operación fue exitosa.

    Raises:
        AppError: AREA_NOT_FOUND (404) si no existe o es de otra empresa.
    """
    prior = repo.find_by_id(str(id), empresa_id)
    if not prior or not repo.delete(str(id), empresa_id):
        raise AppError(*_NO_ENCONTRADA)
    audit.registrar(**payload_baja_area(prior, usuario_id))
    logger.info("Área eliminada", extra={"area_id": str(id)})
    return True
