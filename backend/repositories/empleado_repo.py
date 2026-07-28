"""
Repositorio de empleados — lecturas. Interfaz pública: find_all · find_by_id · find_by_legajo ·
find_by_dni, más las escrituras delegadas (save · update · soft_delete · dar_de_baja).
Todas las operaciones reciben empresa_id para filtrado multiempresa.

Estaba en 174 líneas contra un límite de 100. Se partió en tres: las primitivas compartidas
(tabla, SELECT, mapper) en _empleado_row.py y el write path en _empleado_write_repo.py.
"""
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._empleado_row import SELECT, TABLE, row, with_empresa
from repositories._empleado_write_repo import actualizar, baja_logica, dar_de_baja, guardar
from schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoUpdate


class EmpleadoRepo:
    def find_all(
        self,
        page: int,
        page_size: int,
        empresa_id: Optional[UUID] = None,
        area_id: Optional[str] = None,
        estado: Optional[str] = None,
        search: Optional[str] = None,
        es_lider: Optional[bool] = None,
        proyecto_ids: Optional[List[str]] = None,
    ) -> Tuple[List[EmpleadoResponse], int]:
        """Retorna la página de empleados con area_nombre resuelto y el total sin paginar.
        proyecto_ids: ids ya resueltos por el service (None = sin filtro de proyecto); [] = nadie."""
        start = (page - 1) * page_size
        end = start + page_size - 1

        query = supabase_admin.table(TABLE).select(SELECT, count="exact")
        query = with_empresa(query, empresa_id)

        if proyecto_ids is not None:
            query = query.in_("id", proyecto_ids)
        if area_id:
            query = query.eq("area_id", area_id)
        if estado:
            query = query.eq("estado", estado)
        if es_lider is not None:
            query = query.eq("es_lider", es_lider)
        if search:
            query = query.or_(
                f"nombre.ilike.%{search}%,apellido.ilike.%{search}%"
            )

        result = query.range(start, end).execute()

        total = result.count if result.count is not None else 0
        return [row(r) for r in result.data], total

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[EmpleadoResponse]:
        """Busca un empleado por UUID. Si empresa_id se provee, valida pertenencia. Devuelve None si no existe o no pertenece."""
        query = with_empresa(
            supabase_admin.table(TABLE).select(SELECT).eq("id", id),
            empresa_id,
        )
        result = query.maybe_single().execute()
        if not result or not result.data:
            return None
        return row(result.data)


    def find_by_legajo(self, legajo: str, empresa_id: UUID) -> Optional[EmpleadoResponse]:
        """Busca un empleado por legajo dentro de la empresa. Devuelve None si no existe."""
        res = (supabase_admin.table(TABLE)
               .select(SELECT)
               .eq("legajo", legajo).eq("empresa_id", str(empresa_id))
               .maybe_single().execute())
        return row(res.data) if res and res.data else None

    def find_by_dni(self, dni: str, empresa_id: UUID) -> Optional[EmpleadoResponse]:
        """Busca un empleado por DNI en la empresa indicada. Devuelve None si no existe."""
        res = supabase_admin.table(TABLE).select(SELECT).eq("dni", dni).eq("empresa_id", str(empresa_id)).maybe_single().execute()
        return row(res.data) if res and res.data else None

    # ── Escrituras (delegadas a _empleado_write_repo) ──

    def save(self, data: EmpleadoCreate, empresa_id: UUID) -> EmpleadoResponse:
        """Alta de empleado. Delegado a _empleado_write_repo.guardar."""
        return guardar(data, empresa_id)

    def update(self, id: str, data: EmpleadoUpdate, empresa_id: Optional[UUID] = None) -> Optional[EmpleadoResponse]:
        """Actualización parcial. Delegado a _empleado_write_repo.actualizar."""
        return actualizar(id, data, empresa_id, self.find_by_id)

    def soft_delete(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        """Baja lógica (solo estado). Delegado a _empleado_write_repo.baja_logica."""
        return baja_logica(id, empresa_id)

    def dar_de_baja(self, empleado_id: str, fecha_egreso: date, empresa_id: Optional[UUID] = None) -> bool:
        """Baja con fecha de egreso. Delegado a _empleado_write_repo.dar_de_baja."""
        return dar_de_baja(empleado_id, fecha_egreso, empresa_id)
