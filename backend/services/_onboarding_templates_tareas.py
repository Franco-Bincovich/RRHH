"""
Tareas de un template de onboarding: alta, edición y baja.

Extraído de `onboarding_templates_service.py`, que estaba en 144/150 y no admitía el endpoint
de export. Molde: `_usuario_alta.py` — funciones libres que reciben sus colaboradores.

POR QUÉ SALIÓ ESTE BLOQUE: las tres comparten una forma que las otras no tienen — gatean el
TEMPLATE padre y después tocan la tabla de tareas. La cadena tarea → template → (empresa ∩
visibilidad) es la razón por la que ninguna valida la tarea por su cuenta, y tenerlas juntas
hace que esa regla se lea de una sola vez en vez de repetida en tres docstrings sueltos.

🔴 EL GATE VA ANTES DE ESCRIBIR, en las tres. `ensure_template_accesible` levanta el 404
canónico —que no distingue "no existe" de "es de otra empresa" de "es privada de otro"— y
tiene que correr antes de cualquier efecto. Este archivo no tiene un camino que llegue al repo
sin haber pasado por él.

⚠️ Vive en `services/`, así que su límite es 150 líneas, como cualquier service. No hereda un
límite más alto por ser un satélite.
"""
from typing import Optional
from uuid import UUID

from schemas.onboarding import TareaCreate, TareaResponse, TareaUpdate
from services._template_scope import ensure_template_accesible
from utils.errors import AppError
from utils.logger import logger


def add_tarea(repo, template_id: UUID, data: TareaCreate, empresa_id: Optional[UUID] = None,
              user_id: Optional[str] = None, rol: Optional[str] = None) -> TareaResponse:
    """
    Agrega una tarea a un template existente.

    ⚠️ Este path llamaba a `repo.get_template` DIRECTO y era el único de los cinco de
    escritura que no pasaba por el gate del service. Ahora usa el helper como sus hermanos.

    Raises:
        AppError: TEMPLATE_NOT_FOUND (404) si no lo alcanza por empresa o por visibilidad.
    """
    tmpl = ensure_template_accesible(repo, template_id, empresa_id, user_id, rol)
    tarea = repo.add_tarea(str(template_id), data.model_dump(), str(tmpl.empresa_id))
    logger.info("Tarea agregada al template", extra={"template_id": str(template_id), "tarea_id": str(tarea.id)})
    return tarea


def update_tarea(repo, template_id: UUID, tarea_id: UUID, data: TareaUpdate,
                 empresa_id: Optional[UUID] = None, user_id: Optional[str] = None,
                 rol: Optional[str] = None) -> TareaResponse:
    """
    Actualiza campos de una tarea del template.

    La tarea se alcanza por su template: gatear el template cubre la cadena tarea → template
    → (empresa ∩ visibilidad); las tareas no se resuelven sueltas.

    Raises:
        AppError: TEMPLATE_NOT_FOUND (404) si no lo alcanza por empresa o por visibilidad.
        AppError: TAREA_NOT_FOUND (404) si la tarea no existe.
    """
    ensure_template_accesible(repo, template_id, empresa_id, user_id, rol)  # gate antes de escribir
    tarea = repo.update_tarea(str(tarea_id), data.model_dump(exclude_none=True))
    if not tarea:
        raise AppError("Tarea no encontrada", "TAREA_NOT_FOUND", 404)
    return tarea


def delete_tarea(repo, template_id: UUID, tarea_id: UUID, empresa_id: Optional[UUID] = None,
                 user_id: Optional[str] = None, rol: Optional[str] = None) -> bool:
    """
    Elimina una tarea del template, previa validación sobre el template padre.

    Raises:
        AppError: TEMPLATE_NOT_FOUND (404) si no lo alcanza por empresa o por visibilidad.
    """
    ensure_template_accesible(repo, template_id, empresa_id, user_id, rol)  # gate antes del borrado
    repo.delete_tarea(str(tarea_id))
    logger.info("Tarea eliminada", extra={"template_id": str(template_id), "tarea_id": str(tarea_id)})
    return True
