"""
Primitivas compartidas del repositorio de empleados: la tabla, el SELECT con joins, el filtro de
empresa, el filtro de ESTADO y el mapper de fila. Aisladas para que el repo de lectura y el de
escritura las compartan sin que ninguno de los dos pase su límite de líneas.

`with_empresa` y `filtro_estado` tienen la MISMA forma —toman una query y devuelven una query— y
por eso viven juntas: son las piezas que `find_all` compone sobre el SELECT.

⚠️ `ordenado` era la tercera y se mudó a `repositories/_empleado_orden.py` el 20/8/2026, al dejar
de ser un `return` de una línea: con los dos órdenes por fecha pasó a ser un vocabulario, una
tabla de traducción y una regla sobre el desempate. Las dos de acá siguen siendo UN predicado
cada una. El porqué completo del corte está en el encabezado de aquel archivo.
"""
from typing import Optional
from uuid import UUID

from schemas.empleado import EmpleadoResponse
from utils.estados_empleado import ESTADO_PREINGRESO

TABLE = "empleados"

# Select con joins resueltos en una sola query (sin N+1): nombre de área, empresa y
# del manager. El manager es un self-join to-one: se embebe por la COLUMNA FK
# (manager:manager_id) en vez del nombre de la constraint — el hint por columna sigue la
# FK hacia empleados.id (dirección many-to-one correcta) y es inmune al nombre autogenerado
# de la constraint, que difiere entre entornos (era el origen del PGRST200 en /api/empleados).
SELECT = (
    "*, areas!empleados_area_id_fkey(nombre), empresas(nombre), "
    "manager:manager_id(nombre, apellido)"
)


def with_empresa(query, empresa_id: Optional[UUID]):
    """Aplica filtro de empresa a una query de Supabase si empresa_id no es None."""
    return query.eq("empresa_id", str(empresa_id)) if empresa_id else query


def filtro_estado(q, estado: Optional[str]):
    """Aplica el filtro de estado del listado, con su DEFAULT: sin `estado` no hay preingresos.

    🔴 EL DEFAULT NO ES "SIN FILTRO", Y ESA ES TODA LA FUNCIÓN. Hasta el 18/8/2026 esto era
    `if estado: q = q.eq("estado", estado)`, o sea que sin parámetro la query no llevaba ningún
    predicado de estado y traía la tabla entera. Con los 31 empleados de producción en `activo`
    eso era invisible; desde la migración 120 significa que **la pantalla de colaboradores
    mezcla gente que todavía no entró**, y el archivo del export también.

    El `else` excluye SOLO `preingreso`, no cualquier cosa que no sea plantilla: `baja` y
    `licencia` siguen apareciendo sin filtro, como siempre. La pantalla de colaboradores no es la
    de próximos ingresos; sí es, y sigue siendo, el lugar donde se ve a quien ya no está.

    ⚠️ Un `estado` explícito manda SIEMPRE, `"preingreso"` incluido: el filtro puede apuntar a
    cualquier valor del CHECK. Esto cambia el default, no esconde ninguna fila.

    Vive acá y no en `empleado_repo` por la misma razón que `with_empresa`: toma una query y
    devuelve una query. No importa `supabase_admin` —recibe la query ya construida—, así
    que no se escapa del parcheo por módulo que usan los tests del repo.
    """
    if estado:
        return q.eq("estado", estado)
    return q.neq("estado", ESTADO_PREINGRESO)


def row(r: dict) -> EmpleadoResponse:
    """Convierte un dict de Supabase en EmpleadoResponse.
    Extrae area_nombre ('areas'), empresa_nombre ('empresas') y manager_nombre ('manager',
    self-join) cuando vienen embebidos. manager_nombre = 'Apellido, Nombre' o None."""
    area_info = r.get("areas")
    empresa_info = r.get("empresas")
    manager_info = r.get("manager")
    data = {
        **{k: v for k, v in r.items() if k not in ("areas", "empresas", "manager")},
        "area_nombre": area_info["nombre"] if isinstance(area_info, dict) else None,
        "empresa_nombre": empresa_info["nombre"] if isinstance(empresa_info, dict) else None,
        "manager_nombre": (
            f"{manager_info['apellido']}, {manager_info['nombre']}"
            if isinstance(manager_info, dict) else None
        ),
    }
    return EmpleadoResponse.model_validate(data)
