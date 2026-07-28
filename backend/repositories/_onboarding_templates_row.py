"""
Primitivas compartidas del repositorio de templates de onboarding: las tablas, los SELECT con
joins, el filtro de empresa y los mappers de fila.

Aisladas por el mismo motivo que `_empleado_row.py` y `_nomina_row.py`: el repo estaba en
99/100 líneas y sumarle el autor (columna + embed + mapeo) lo pasaba. Acá el límite es 200.

⚠️ El autor se embebe por la COLUMNA FK (`creador:created_by`) y no por el nombre de la
constraint. `onboarding_templates` tiene UNA sola FK a `users`, así que hoy `users(nombre)` a
secas tampoco sería ambiguo — pero el hint por columna es inmune a que mañana alguien agregue
una segunda FK a `users` (p. ej. `actualizado_por`), que es justo lo que convierte un embed
que venía andando en un PGRST201 sin tocar el código. Misma decisión, y por el mismo motivo,
que el self-join de manager en `_empleado_row.py`.
"""
from typing import Optional
from uuid import UUID

from schemas.onboarding import TareaResponse, TemplateResponse

TAREAS = "onboarding_tareas"
TEMPLATES = "onboarding_templates"
INSTANCIAS = "onboarding_instancias"

# 🔴 El embed de tareas NOMBRA la FK, y no es opcional. Hay DOS relaciones entre
# onboarding_tareas y onboarding_templates: la simple (template_id) y la compuesta
# (template_id, empresa_id) que agregó el retrofit multiempresa. Con dos caminos PostgREST no
# elige: responde 300 PGRST201 y el endpoint no devuelve datos. Mismo caso que las 2 FKs de
# costos_nomina a empleados. `tests/test_onboarding_template_autor.py` valida estos dos
# strings contra db/schema.sql para que no vuelva a pasar.
_TAREAS_FK = f"{TAREAS}!onboarding_tareas_template_id_fkey"

# Columnas de la tarea cuando viene embebida en el detalle del template.
TAREA_COLS = f"{_TAREAS_FK}(id,template_id,nombre,descripcion,semana,orden)"

_BASE = "id,empresa_id,nombre,descripcion,created_by,empresas(nombre),creador:created_by(nombre)"

# El listado solo necesita CONTAR tareas; el detalle las trae enteras.
SELECT_LISTA = f"{_BASE},{_TAREAS_FK}(id)"
SELECT_DETALLE = f"{_BASE},{TAREA_COLS}"


def with_empresa(query, empresa_id: Optional[UUID]):
    """Aplica filtro de empresa a una query de Supabase si empresa_id no es None."""
    return query.eq("empresa_id", str(empresa_id)) if empresa_id else query


def tarea(t: dict) -> TareaResponse:
    """Convierte una fila de `onboarding_tareas` en TareaResponse.

    La columna se llama `nombre` en la tabla y `titulo` en la API: la traducción vive acá, en
    el único lugar que lee esa fila.
    """
    return TareaResponse(
        id=t["id"], template_id=t["template_id"], titulo=t["nombre"],
        descripcion=t.get("descripcion"), semana=t.get("semana", 1), orden=t.get("orden", 1),
    )


def template(r: dict, tareas: Optional[list[TareaResponse]] = None) -> TemplateResponse:
    """Convierte una fila de `onboarding_templates` en TemplateResponse.

    Resuelve los dos joins embebidos (`empresas`, `creador`) a sus nombres. Con `tareas=None`
    —el caso del listado— las tareas quedan vacías y `tareas_total` sale del conteo que trajo
    el embed liviano.

    `created_by_nombre` queda en None cuando el template no tiene autor: o es anterior al
    cableado del autor, o su usuario se borró (la FK es ON DELETE SET NULL). Los dos casos se
    ven igual desde acá y ninguno es un error.
    """
    empresa_info = r.get("empresas")
    creador_info = r.get("creador")
    total = len(tareas) if tareas is not None else len(r.get(TAREAS) or [])
    return TemplateResponse(
        id=r["id"], nombre=r["nombre"], descripcion=r.get("descripcion"),
        empresa_id=r.get("empresa_id"),
        empresa_nombre=empresa_info["nombre"] if isinstance(empresa_info, dict) else None,
        created_by=r.get("created_by"),
        created_by_nombre=creador_info["nombre"] if isinstance(creador_info, dict) else None,
        tareas=tareas or [], tareas_total=total,
    )
