"""
Primitivas compartidas del repositorio de empleados: la tabla, el SELECT con joins, el filtro
de empresa y el mapper de fila. Aisladas para que el repo de lectura y el de escritura las
compartan sin que ninguno de los dos pase su límite de líneas.
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
