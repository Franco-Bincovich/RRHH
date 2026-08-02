"""
Lookups de UNA fila de empleado por identidad: por PK (id), por legajo y por DNI. Extraído de
empleado_repo.py, que estaba en 98 líneas contra un límite de 100 y no admitía un filtro más
en `find_all`.

El corte es por forma de la lectura, no por capricho de líneas: acá vive "traeme ESTE empleado"
y en el principal queda "traeme LA LISTA", que es la que crece con cada filtro nuevo.

Reusa SELECT/with_empresa/row de _empleado_row (fuente de verdad única del JOIN y del mapper):
un satélite que devuelve EmpleadoResponse NO redefine la query ni el mapper — los importa.

Molde: migracionAWS/backend/repositories/empleado_lookup_repo_NEW.py, con dos diferencias
deliberadas. Allá el satélite se lleva además `soft_delete`/`dar_de_baja` y deja `find_by_id`
en el principal; acá las dos bajas ya viven en _empleado_write_repo (así que moverlas las
volvería delegadores dobles) y `find_by_id` sí entra, porque es el mismo tipo de lectura que
las otras dos. El nombre de archivo se mantiene para que el port a asyncpg aterrice acá.
"""
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._empleado_row import SELECT, TABLE, row, with_empresa
from schemas.empleado import EmpleadoResponse


def por_id(id: str, empresa_id: Optional[UUID] = None) -> Optional[EmpleadoResponse]:
    """Busca un empleado por UUID. Si empresa_id se provee, valida pertenencia.
    Devuelve None si no existe o no pertenece — el 404 idéntico lo arma el service."""
    query = with_empresa(
        supabase_admin.table(TABLE).select(SELECT).eq("id", id),
        empresa_id,
    )
    result = query.maybe_single().execute()
    if not result or not result.data:
        return None
    return row(result.data)


def por_legajo(legajo: str, empresa_id: UUID) -> Optional[EmpleadoResponse]:
    """Busca un empleado por legajo dentro de la empresa. Devuelve None si no existe."""
    res = (supabase_admin.table(TABLE)
           .select(SELECT)
           .eq("legajo", legajo).eq("empresa_id", str(empresa_id))
           .maybe_single().execute())
    return row(res.data) if res and res.data else None


def por_dni(dni: str, empresa_id: UUID) -> Optional[EmpleadoResponse]:
    """Busca un empleado por DNI en la empresa indicada. Devuelve None si no existe."""
    res = supabase_admin.table(TABLE).select(SELECT).eq("dni", dni).eq("empresa_id", str(empresa_id)).maybe_single().execute()
    return row(res.data) if res and res.data else None
