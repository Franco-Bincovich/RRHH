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
from typing import List, Optional
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


def indice_por_nombre() -> List[dict]:
    """Nombre+apellido de TODOS los empleados, de TODAS las empresas, en UNA sola query.

    Es la excepción a la regla de este módulo ("traeme ESTE empleado"): devuelve muchas filas. Vive
    igual acá porque su eje es el mismo —identidad, no filtros— y porque `empleado_repo.py` está en
    96/100 líneas, donde `find_all` es justamente lo que crece con cada filtro nuevo.

    🔴 NO ACOTA POR EMPRESA, Y ES LA DECISIÓN IMPORTANTE DE ESTA FUNCIÓN. Lo usa el resolver de
    superiores del import de nómina, y un empleado puede tener superior de OTRA EMPRESA DEL GRUPO
    (decisión de producto 2/8/2026, ver `services/_alcance_mandos.py`).

    Se probó acotarlo a las empresas presentes en el archivo, que suena razonable y no lo es: el
    jefe puede trabajar en una empresa que NO tiene ni una fila en el CSV que se está importando
    (se importa la nómina de ACME y el superior está cargado en DOSUBA). Ese recorte no da error
    —devuelve "no hay ningún empleado con ese nombre"— y dejaría sin resolver exactamente los
    superiores cruzados, que son el caso que motivó todo el cambio. Un filtro que falla en silencio
    justo en su caso de uso es peor que una lectura de más.

    ⚠️ EL COSTO, dicho sin maquillar: es una lectura full-table. Se banca porque son 4 columnas,
    UNA vez por import (no por fila), sobre un padrón de 2–5 empresas —19 empleados hoy—, dentro de
    la operación más pesada que tiene la app y que ya corre con presupuesto de tiempo propio.
    🚩 Disparador para revisarlo: que el padrón pase de unos pocos miles de empleados. La salida
    entonces NO es volver a acotar por empresa (mismo bug silencioso) sino un índice normalizado en
    la base —columna generada + índice— para poder preguntar por nombre en el WHERE.

    Devuelve dicts crudos y NO `EmpleadoResponse`: acá se arma un índice en memoria con 4 campos,
    y pagar el `SELECT` con joins de `_empleado_row` por cada empleado sería traer área, manager y
    empresa resueltos para descartarlos en la línea siguiente.

    Returns:
        Lista de dicts `{id, nombre, apellido, empresa_id}`. [] si no hay.
    """
    res = supabase_admin.table(TABLE).select("id, nombre, apellido, empresa_id").execute()
    return res.data or []
