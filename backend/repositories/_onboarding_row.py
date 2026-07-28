"""
Primitivas compartidas del repositorio de onboarding: las tablas, el SELECT con joins, el
filtro de empresa y los mappers de fila.

Aisladas por el mismo motivo que `_onboarding_templates_row.py` y `_empleado_row.py`: el repo
estaba en 100/100 líneas y no admitía un cambio más. Acá el límite es 200.

⚠️ Los tres embeds NOMBRAN su FK, y no es decorativo: `onboarding_instancias` y
`onboarding_progreso` tienen cada una DOS relaciones con su padre (la simple y la compuesta
con `empresa_id` que agregó el retrofit multiempresa). Sin el hint, PostgREST no elige y
responde 300 PGRST201 en vez de datos.
"""
from typing import Optional
from uuid import UUID

from schemas.onboarding import InstanciaResponse, TareaProgresoResponse

INSTANCIAS = "onboarding_instancias"
PROGRESO = "onboarding_progreso"
TAREAS = "onboarding_tareas"
TEMPLATES = "onboarding_templates"

# Empleado + área + empresa de la instancia, resueltos en una sola query (sin N+1).
JOIN_EMPLEADO = (
    "empleados!onboarding_instancias_empleado_id_fkey"
    "(nombre,apellido,roles,areas!empleados_area_id_fkey(nombre)), empresas(nombre)"
)

# Estados que ya no cuentan como onboarding "activo".
EXCLUIDOS = ["completado", "cancelado"]


def with_empresa(q, empresa_id: Optional[UUID]):
    """Aplica filtro de empresa a una query de Supabase si empresa_id no es None."""
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


def instancia_row(r: dict, progs: Optional[list] = None) -> InstanciaResponse:
    """Convierte una fila de `onboarding_instancias` en InstanciaResponse.

    El progreso se calcula sobre las filas de `onboarding_progreso`: con `progs` explícito
    (detalle, que ya las trajo por separado) o con las que vinieron embebidas (listado).
    """
    emp = r.get("empleados") or {}
    area = emp.get("areas") or {}
    empresa = r.get("empresas") or {}
    ps = progs if progs is not None else (r.get(PROGRESO) or [])
    total = len(ps)
    done = sum(1 for p in ps if p.get("estado") == "completado")
    return InstanciaResponse(
        id=r["id"], empleado_id=r["empleado_id"],
        empresa_id=r.get("empresa_id"), empresa_nombre=empresa.get("nombre"),
        empleado_nombre=f"{emp.get('nombre', '')} {emp.get('apellido', '')}".strip(),
        empleado_cargo=(emp.get("roles") or [emp.get("cargo")])[0], empleado_area=area.get("nombre"),
        template_id=r["template_id"], estado=r["estado"],
        fecha_inicio=str(r.get("fecha_inicio", "")),
        progreso=round(done / total * 100) if total else 0,
        tareas_completadas=done, tareas_total=total,
    )


def tarea_progreso_row(p: dict) -> TareaProgresoResponse:
    """Convierte una fila de `onboarding_progreso` (con su tarea embebida) en TareaProgresoResponse."""
    t = p.get(TAREAS) or {}
    return TareaProgresoResponse(
        progreso_id=p["id"], tarea_id=p["tarea_id"], titulo=t.get("nombre", ""),
        descripcion=t.get("descripcion"), semana=t.get("semana", 1), orden=t.get("orden", 1),
        completada=p.get("estado") == "completado",
    )
