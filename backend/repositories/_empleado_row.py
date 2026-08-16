"""
Primitivas compartidas del repositorio de empleados: la tabla, el SELECT con joins, el filtro de
empresa, el ORDEN del listado y el mapper de fila. Aisladas para que el repo de lectura y el de
escritura las compartan sin que ninguno de los dos pase su límite de líneas.

`with_empresa` y `ordenado` tienen la MISMA forma —toman una query y devuelven una query— y por
eso viven juntas: son las dos piezas que `find_all` compone sobre el SELECT.
"""
from typing import Optional
from uuid import UUID

from schemas.empleado import EmpleadoResponse

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


def ordenado(q):
    """Aplica el orden TOTAL del listado: apellido, nombre y el desempate por `id`.

    🔴 HASTA EL 14/8/2026 ESTE LISTADO PAGINABA SIN NINGÚN `.order()`. Un `.range()` sobre un
    SELECT sin orden le deja a Postgres elegir el orden de las filas, y no tiene por qué elegir
    el mismo en dos consultas distintas: la página 2 podía repetir a alguien de la 1 o saltearlo.
    No daba error ni se veía en los tests — se veía como un empleado que "no está en la lista".

    🔴 EL `id` NO ES DECORACIÓN. `apellido, nombre` no es un orden TOTAL: en el padrón de escala
    411 de 1.005 personas comparten los dos campos con alguien. Entre empatados, Postgres tampoco
    garantiza un orden estable entre ejecuciones, así que sin el desempate el bug de arriba
    sobrevive en su versión chica.

    ⚠️ El `id` va ASCENDENTE. El índice que sirve esta consulta —`idx_empleados_empresa_apellido
    (empresa_id, apellido, nombre, id)`, migración 118— se creó con esa forma exacta; pedir el
    desempate al revés obligaría a un nodo de sort que el índice existe para evitar.
    """
    return q.order("apellido").order("nombre").order("id")


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
