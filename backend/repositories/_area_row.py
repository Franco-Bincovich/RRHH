"""
Primitivas compartidas del repositorio de áreas: la tabla, el SELECT con el join del
responsable, la QUERY BASE del listado, el conteo de empleados por área y el mapper de fila.

SALIÓ DE `area_repo.py`, que estaba en 100/100 cuando le tocaba sumar la paginación y el filtro
de búsqueda. Molde: `_empleado_row.py`, `_nomina_row.py`, `_hora_row.py`.

🔴 `counts_by_area()` CONSULTA LA TABLA ENTERA DE EMPLEADOS, y eso NO cambia al paginar áreas.
Trae un `area_id` por empleado activo y cuenta en Python — con 1.005 colaboradores son 1.005
enteros, no 1.005 filas de legajo. Paginar el listado de áreas recorta las ÁREAS, no la base
sobre la que se cuenta: el conteo de un área tiene que ser el de toda su gente, no el de la
gente que entró en la página. Por eso el conteo se hace una vez y se pasa al mapper, en vez de
resolverse por fila.

⚠️ Excluye `estado = 'baja'` y NO excluye `licencia`: alguien de licencia sigue siendo headcount
del área. Es una decisión de producto, no un filtro olvidado.
"""
from typing import Optional

from integrations.supabase_client import supabase_admin
from schemas.area import AreaResponse

TABLE = "areas"
SELECT = "*, empleados!fk_areas_responsable(nombre, apellido)"

_EMPLEADOS_TABLE = "empleados"


def base(empresa_id: Optional[str], search: Optional[str], contar: bool):
    """La query del listado de áreas activas. UNA definición para el catálogo y la página.

    `search` va con `.ilike("nombre", "%...%")`, o sea EN EL WHERE. Hasta el 15/8/2026 el
    buscador de áreas filtraba sobre el array ya traído (`useAreas.ts:46`), y eso tenía dos
    consecuencias que sólo se ven cuando el listado crece:
      · con paginación, buscás algo que existe pero está en la página 3 y la pantalla dice que
        no hay resultados — sin error, porque el filtro nunca vio esa fila;
      · el EXPORT no veía el filtro, así que buscabas algo y el archivo salía con todo
        (invariante 1 del bloque B: si el filtro afecta al export, va server-side).
    """
    q = supabase_admin.table(TABLE).select(SELECT, count="exact") if contar \
        else supabase_admin.table(TABLE).select(SELECT)
    q = q.eq("activo", True)
    if empresa_id:
        q = q.eq("empresa_id", empresa_id)
    if search:
        q = q.ilike("nombre", f"%{search}%")
    return q


def counts_by_area() -> dict[str, int]:
    """Cuántos empleados NO dados de baja tiene cada área. {} si no hay ninguno."""
    # Excluye 'baja': licencia sigue siendo headcount del área
    rows = supabase_admin.table(_EMPLEADOS_TABLE).select("area_id").neq("estado", "baja").execute().data or []
    counts: dict[str, int] = {}
    for row in rows:
        if aid := row.get("area_id"):
            counts[aid] = counts.get(aid, 0) + 1
    return counts


def to_response(row: dict, counts: dict[str, int]) -> AreaResponse:
    """Fila cruda de `areas` → AreaResponse, con el responsable y el headcount resueltos.

    ⚠️ NO expone `area_padre_id` aunque la columna exista (`idx_areas_padre`): el listado de
    áreas es PLANO y nunca mostró la jerarquía. Sumarla acá no es agregar un campo — es cambiar
    la forma del listado, y con eso lo que `total` significa al paginar (raíces vs nodos, la
    misma vuelta que tiene objetivos). Si algún día se muestra el árbol, se decide eso primero.
    """
    emp = row.get("empleados") or {}
    responsable_nombre = (
        f"{emp.get('nombre', '')} {emp.get('apellido', '')}".strip() or None
    )
    return AreaResponse(
        id=str(row["id"]),
        empresa_id=str(row["empresa_id"]) if row.get("empresa_id") else None,
        nombre=row["nombre"],
        descripcion=row.get("descripcion"),
        responsable_id=str(row["responsable_id"]) if row.get("responsable_id") else None,
        responsable_nombre=responsable_nombre,
        cantidad_empleados=counts.get(str(row["id"]), 0),
        created_at=row["created_at"],
    )
