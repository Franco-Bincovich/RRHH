"""
Escrituras de la VACANTE en sí: alta, edición y baja.

Extraído de `vacante_service.py`, que estaba en 147/150 y no admitía el endpoint de export.
Molde: `_vacante_candidatos.py` (el satélite hermano, que se llevó las escrituras del
CANDIDATO) y `_empresa_logo.py` — funciones libres que reciben sus colaboradores.

POR QUÉ SALIÓ ESTE BLOQUE: las tres arman su payload de auditoría INLINE, y eso es la mitad de
sus líneas. Son además las tres que mutan la fila de `vacantes`; lo que queda en el service son
lecturas y la delegación a los candidatos. El corte cae en la misma costura que ya había
separado `_vacante_candidatos`.

🔴 EL ORDEN DEL BORRADO ES LOAD-BEARING y por eso viaja completo con `eliminar`: congelar el
nombre de la búsqueda en los candidatos va ANTES de borrar la vacante, porque después la FK
queda en NULL (migración 071) y el texto ya no se puede reconstruir.

⚠️ Vive en `services/`, así que su límite es 150 líneas, como cualquier service. No hereda un
límite más alto por ser un satélite.
"""
from typing import Optional
from uuid import UUID

from schemas.vacante import VacanteCreate, VacanteResponse, VacanteUpdate
from utils.errors import AppError
from utils.logger import logger

_ESTADOS = {"nueva", "en_proceso", "con_candidatos", "cerrada"}


def _or_404(vacante: Optional[VacanteResponse]) -> VacanteResponse:
    """Literal ÚNICO del 404 del módulo: "no existe" y "es de otra empresa" son el mismo caso."""
    if not vacante:
        raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
    return vacante


def crear(repo, audit, data: VacanteCreate, created_by: str) -> VacanteResponse:
    """
    Crea una nueva vacante en estado 'nueva'. empresa_id viene en el body.

    Args:
        repo: VacanteRepo (o doble de test).
        audit: AuditService (o doble de test).
        data: Datos de la vacante validados por Pydantic (incluye empresa_id).
        created_by: ID del usuario que realiza la operación (trazabilidad).
    """
    vacante = repo.save(data)
    audit.registrar(
        usuario_id=created_by, entidad="vacante", registro_id=vacante.id, accion="INSERT",
        evento="alta_vacante", empresa_id=vacante.empresa_id, datos_anteriores=None,
        datos_nuevos={"titulo": vacante.titulo, "area_id": vacante.area_id, "estado": vacante.estado},
    )
    logger.info("Vacante creada", extra={"vacante_id": vacante.id, "created_by": created_by})
    return vacante


def actualizar(repo, audit, id: UUID, data: VacanteUpdate, empresa_id: Optional[UUID] = None,
               usuario_id: Optional[str] = None) -> VacanteResponse:
    """
    Actualiza los campos de una vacante existente (actualización parcial).

    Raises:
        AppError: ESTADO_INVALIDO (400) si el estado no está en el enum.
        AppError: VACANTE_NOT_FOUND (404) si el ID no existe o no pertenece a la empresa.
    """
    if data.estado and data.estado not in _ESTADOS:
        raise AppError(
            f"Estado inválido. Permitidos: {', '.join(_ESTADOS)}", "ESTADO_INVALIDO", 400
        )
    # Lectura previa para el diff: `update` devuelve la fila YA actualizada, así que sin esto
    # el evento no podría decir de qué valor se venía. El 404 es el mismo de abajo.
    previa = _or_404(repo.find_by_id(str(id), empresa_id))
    vacante = _or_404(repo.update(str(id), data, empresa_id))
    tocados = data.model_dump(exclude_none=True)
    audit.registrar(
        usuario_id=usuario_id, entidad="vacante", registro_id=str(id), accion="UPDATE",
        evento="edicion_vacante", empresa_id=vacante.empresa_id,
        datos_anteriores={k: getattr(previa, k, None) for k in tocados},
        datos_nuevos={k: getattr(vacante, k, None) for k in tocados},
    )
    logger.info("Vacante actualizada", extra={"vacante_id": str(id)})
    return vacante


def eliminar(repo, candidato_repo, adjuntos, audit, id: UUID, empresa_id: Optional[UUID] = None,
             rol: Optional[str] = None, usuario_id: Optional[str] = None) -> None:
    """Elimina la vacante. Orden estricto: (1) congela el nombre en sus candidatos (sobreviven
    vía FK SET NULL, migración 071), (2) borra físicamente + soft-delete sus imágenes, (3) borra
    la fila. Raises VACANTE_NOT_FOUND (404)."""
    vac = _or_404(repo.find_by_id(str(id), empresa_id))
    texto = f"{vac.titulo} — {vac.area_nombre}" if vac.area_nombre else vac.titulo
    candidato_repo.congelar_busqueda(str(id), texto, empresa_id)  # ANTES de borrar la vacante
    adjuntos.eliminar_todos_por_entidad("vacante", str(id), empresa_id, rol, usuario_id)
    repo.delete(str(id), empresa_id)
    audit.registrar(
        usuario_id=usuario_id, entidad="vacante", registro_id=str(id), accion="DELETE",
        evento="baja_vacante", empresa_id=vac.empresa_id,
        datos_anteriores={"titulo": vac.titulo}, datos_nuevos=None,
    )
    logger.info("Vacante eliminada", extra={"vacante_id": str(id)})
