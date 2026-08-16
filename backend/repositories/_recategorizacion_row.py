"""
Mapper de `recategorizaciones`: fila cruda → `RecategorizacionResponse`, con los tres nombres
resueltos POR LOTE.

🔴 LOS NOMBRES SE RESUELVEN CON LOOKUPS BATCH Y NO CON EMBEDS DE POSTGREST, y es una decisión.
`recategorizaciones` tiene una FK COMPUESTA a `empleados` (`recat_empleado_empresa_fk`), y un
embed `empleados(nombre)` sobre una relación compuesta es justo la clase de spec que PostgREST
resuelve de forma no obvia — y el día que alguien agregue una segunda FK entre las dos tablas
pasa a ser ambiguo y responde **300 PGRST201**, con el único síntoma de una pantalla en blanco.
El repo ya pagó eso con seis reportes rotos en producción.

Con lookups batch el problema no existe: son tres selects de columnas planas, uno por dimensión,
sin ninguna relación declarada. Molde textual: `audit_repo._build`.

⚠️ **NO ES N+1.** Se juntan los ids de TODA la página y se hace UNA query por dimensión (tres en
total, sin importar si la página trae 1 fila o 100). El anti-patrón sería consultar por fila.

Los tres nombres son DERIVADOS: no son datos de la fila sino resultado de cómo se la leyó. Por
eso quedan fuera del diff de auditoría (`_DERIVADOS_RECAT`), que es el bug del "diff fantasma"
que este repo ya cerró una vez.
"""
from typing import List

from integrations.supabase_client import supabase_admin
from schemas.recategorizacion import RecategorizacionResponse

TABLE = "recategorizaciones"

# Columnas de la tabla, sin embeds. El `*` sería equivalente hoy, pero enumerar deja el spec
# validable por `tests/test_selects_repos.py` contra `db/schema.sql`.
SELECT = ("id, empresa_id, empleado_id, fecha_efectiva, rol_anterior, rol_nuevo, "
          "seniority_anterior, seniority_nueva, categoria_anterior, categoria_nueva, "
          "motivo, impacto_salarial, registrado_por, created_at, updated_at")


def _mapa(tabla: str, ids: list, campos: str, armar) -> dict:
    """{id: etiqueta} para un lote de ids. Dict vacío si no hay ids (no consulta al pedo)."""
    if not ids:
        return {}
    filas = supabase_admin.table(tabla).select(campos).in_("id", ids).execute().data or []
    return {f["id"]: armar(f) for f in filas}


def build(rows: List[dict]) -> List[RecategorizacionResponse]:
    """Enriquece un lote de filas con empleado, empresa y quién la registró.

    Los tres quedan en None si el id es NULL o no se encuentra (p. ej. un usuario borrado:
    `registrado_por` es FK `ON DELETE SET NULL`). Un nombre que no resuelve no puede tumbar la
    lectura del histórico.
    """
    if not rows:
        return []
    emp_map = _mapa("empleados", list({r["empleado_id"] for r in rows if r.get("empleado_id")}),
                    "id, nombre, apellido", lambda f: f"{f['apellido']}, {f['nombre']}")
    empresa_map = _mapa("empresas", list({r["empresa_id"] for r in rows if r.get("empresa_id")}),
                        "id, nombre", lambda f: f["nombre"])
    user_map = _mapa("users", list({r["registrado_por"] for r in rows if r.get("registrado_por")}),
                     "id, nombre, apellido", lambda f: f"{f['nombre']} {f['apellido']}")
    return [
        RecategorizacionResponse.model_validate({
            **r,
            "empleado_nombre": emp_map.get(r.get("empleado_id")),
            "empresa_nombre": empresa_map.get(r.get("empresa_id")),
            "registrado_por_nombre": user_map.get(r.get("registrado_por")),
        })
        for r in rows
    ]


def con_empresa(q, empresa_id):
    """Aplica el filtro de empresa si viene. None = consolidado, no restringe.

    Vive con `TABLE`/`SELECT`/`build` y no en el repo porque es la MISMA clase de primitiva:
    toma una query y devuelve una query. Molde: `_empleado_row.with_empresa`.
    """
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q
