"""
Repo satélite de empleados (molde) — lookups por identidad de negocio + las dos bajas.
Separado de empleado_repo_NEW para que el principal quede bajo el límite de 100 líneas,
mismo patrón que RRHH ya usa (empleado_ownership_repo / empleado_roles_repo). Rebalanceo:
soft_delete y dar_de_baja viven acá (ambas son "baja") para no pasar el límite en el
principal. DESTINO al migrar: repositories/empleado_lookup_repo.py.

Reusa _SELECT y _row del principal (fuente de verdad única del JOIN y del mapper): un
satélite que devuelve EmpleadoResponse NO redefine la query ni el mapper — los importa.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from integrations.postgres_client import fetchone, fetchval
from repositories.empleado_repo_NEW import _SELECT, _row
from schemas.empleado import EmpleadoResponse

_TABLE = "empleados"


class EmpleadoLookupRepo:
    async def find_by_dni(self, dni: str, empresa_id: UUID) -> Optional[EmpleadoResponse]:
        """Busca por DNI dentro de la empresa (empresa_id obligatorio, no consolida). None si no existe."""
        row = await fetchone(
            _SELECT + " WHERE e.dni = $1 AND e.empresa_id = $2",
            dni, empresa_id,
        )
        return _row(row) if row else None

    async def find_by_legajo(self, legajo: str, empresa_id: UUID) -> Optional[EmpleadoResponse]:
        """Busca por legajo dentro de la empresa (obligatorio). None si no existe."""
        row = await fetchone(
            _SELECT + " WHERE e.legajo = $1 AND e.empresa_id = $2",
            legajo, empresa_id,
        )
        return _row(row) if row else None

    async def soft_delete(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        """Marca estado='baja' (sin fecha). RETURNING id → bool (True si tocó una fila)."""
        got = await fetchval(
            "UPDATE " + _TABLE + " SET estado = 'baja' WHERE id = $1"
            " AND ($2::uuid IS NULL OR empresa_id = $2) RETURNING id",
            UUID(str(id)), empresa_id,
        )
        return got is not None

    async def dar_de_baja(self, empleado_id: str, fecha_egreso: date, empresa_id: Optional[UUID] = None) -> bool:
        """Baja con fecha de egreso (estado='baja' + fecha_egreso) en un solo UPDATE.
        TIPOS: fecha_egreso se bindea nativo (date), sin str(). True si tocó una fila."""
        got = await fetchval(
            "UPDATE " + _TABLE + " SET estado = 'baja', fecha_egreso = $1 WHERE id = $2"
            " AND ($3::uuid IS NULL OR empresa_id = $3) RETURNING id",
            fecha_egreso, UUID(str(empleado_id)), empresa_id,
        )
        return got is not None
