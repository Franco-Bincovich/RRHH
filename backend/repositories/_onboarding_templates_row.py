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

_BASE = ("id,empresa_id,nombre,descripcion,created_by,es_publica,"
         "empresas(nombre),creador:created_by(nombre)")

# El listado solo necesita CONTAR tareas; el detalle las trae enteras.
SELECT_LISTA = f"{_BASE},{_TAREAS_FK}(id)"
SELECT_DETALLE = f"{_BASE},{TAREA_COLS}"


def with_empresa(query, empresa_id: Optional[UUID]):
    """Aplica filtro de empresa a una query de Supabase si empresa_id no es None."""
    return query.eq("empresa_id", str(empresa_id)) if empresa_id else query


# Rol que ve TODAS las plantillas, incluidas las privadas de los demás. Ver with_visibilidad.
ROL_VE_TODO = "gerencia_lectura"


def with_visibilidad(query, user_id: Optional[str], rol: Optional[str] = None):
    """Acota la query a las plantillas que `user_id` puede ver. LA REGLA VIVE SOLO ACÁ.

        es_publica = true  OR  created_by = user_id  OR  created_by IS NULL

    Va en el WHERE (Forma A) y no en Python: es una sola ida a la base, no trae filas que el
    usuario no puede ver, y el listado no puede "olvidarse" de filtrar. La misma expresión la
    usan el listado, el detalle y la plantilla por defecto, así que no hay dos criterios que
    puedan separarse.

    `created_by IS NULL` cuenta como pública: la FK del autor es ON DELETE SET NULL, así que
    borrar un usuario dejaría sus privadas sin dueño y un filtro por autor las volvería
    inalcanzables para siempre. Ver la migración 082.

    🔴 `gerencia_lectura` NO SE FILTRA: ve todas, incluidas las privadas ajenas. No es una
    excepción al modelo de roles — es lo que ese rol YA significa en todo el sistema ("lectura
    en todo"), y respetarlo acá es lo que evita abrir la PRIMERA excepción row-level. "Privada"
    en este módulo es privacidad ENTRE PARES DE RRHH (un borrador que no quiero que aparezca en
    la lista de mis compañeros), no confidencialidad frente a la dirección. Si algún día hace
    falta ocultárselas también a gerencia, se agrega acá; al revés no se puede.

    ⚠️ `user_id=None` NO restringe, igual que `empresa_id=None`. No es un modo de acceso: es
    para la relectura posterior a una escritura ya gateada (`update_template`), donde volver a
    filtrar podría devolver None sobre una fila que el caller acaba de editar legítimamente.
    Ningún camino que venga del router llega acá sin user_id — AuthMiddleware es fail-closed.

    Args:
        query: Query de Supabase en construcción.
        user_id: UUID en texto del usuario que mira. None = sin restricción.
        rol: Rol del usuario. `gerencia_lectura` no se filtra.

    Returns:
        La query con el filtro aplicado.
    """
    if user_id is None or rol == ROL_VE_TODO:
        return query
    return query.or_(f"es_publica.eq.true,created_by.is.null,created_by.eq.{user_id}")


def tarea(t: dict) -> TareaResponse:
    """Convierte una fila de `onboarding_tareas` en TareaResponse.

    La columna se llama `nombre` en la tabla y `titulo` en la API: la traducción vive acá, en
    el único lugar que lee esa fila.
    """
    return TareaResponse(
        id=t["id"], template_id=t["template_id"], titulo=t["nombre"],
        descripcion=t.get("descripcion"), semana=t.get("semana", 1), orden=t.get("orden", 1),
    )


def payload_template(nombre: str, descripcion: Optional[str], empresa_id: UUID,
                     created_by: Optional[str]) -> dict:
    """Fila de `onboarding_templates` a insertar.

    `es_publica` NO va: se deja al default de la columna (true, migración 082). Una plantilla
    nace compartida y se vuelve privada por decisión explícita de su autor desde el detalle.
    """
    return {"nombre": nombre, "descripcion": descripcion, "activo": True,
            "empresa_id": str(empresa_id), "created_by": created_by}


def payload_tarea(template_id: str, empresa_id: str, data: dict) -> dict:
    """Fila de `onboarding_tareas` a insertar. La tarea hereda el empresa_id de su plantilla.

    Traduce `titulo` (API) a `nombre` (columna) y aplica los defaults de las columnas que la
    UI todavía no expone (`responsable_tipo`, `dias_limite`).
    """
    return {
        "template_id": template_id, "empresa_id": str(empresa_id), "nombre": data["titulo"],
        "descripcion": data.get("descripcion"), "semana": data["semana"],
        "orden": data["orden"], "responsable_tipo": data.get("responsable_tipo", "rrhh"),
        "dias_limite": data.get("dias_limite", 1),
    }


def payload_tarea_update(data: dict) -> dict:
    """Campos a actualizar de una tarea, sin los ausentes. Vacío = nada que hacer."""
    campos = {"nombre": data.get("titulo"), "descripcion": data.get("descripcion"),
              "semana": data.get("semana"), "orden": data.get("orden")}
    return {k: v for k, v in campos.items() if v is not None}


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
        # Default true: es el de la columna (migración 082) y el que corresponde a una fila
        # que vuelve de un INSERT sin haberla releído.
        es_publica=r.get("es_publica", True),
        tareas=tareas or [], tareas_total=total,
    )
