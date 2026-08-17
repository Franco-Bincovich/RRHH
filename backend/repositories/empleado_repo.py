"""
Repositorio de empleados — lecturas. Interfaz pública: find_all · find_by_id · find_by_legajo ·
find_by_dni, más las escrituras delegadas (save · update · dar_de_baja).
Todas las operaciones reciben empresa_id para filtrado multiempresa.

Estaba en 174 líneas contra un límite de 100. Se partió en cuatro: las primitivas compartidas
(tabla, SELECT, mapper) en _empleado_row.py, el write path en _empleado_write_repo.py y los
lookups de una fila en _empleado_lookup_repo.py. Acá queda `find_all` —el listado, que es lo
único que crece con cada filtro nuevo— más los delegadores que sostienen la interfaz pública.
"""
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._empleado_lookup_repo import por_dni, por_id, por_legajo
from repositories._empleado_row import SELECT, TABLE, ordenado as _ordenado, row, with_empresa
from repositories._empleado_write_repo import actualizar, dar_de_baja, guardar
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
        sin_manager: Optional[bool] = None,
    ) -> Tuple[List[EmpleadoResponse], int]:
        """Retorna la página de empleados con area_nombre resuelto y el total sin paginar.
        proyecto_ids: ids ya resueltos por el service (None = sin filtro de proyecto); [] = nadie.
        sin_manager: True = solo los que no tienen superior · False = solo los que sí · None = sin filtro."""
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
        if sin_manager is not None:
            # `False` es un filtro válido ("solo los que SÍ tienen superior"), no un vacío:
            # por eso el chequeo es `is not None` y no la verdad del booleano.
            query = query.is_("manager_id", "null") if sin_manager else query.not_.is_("manager_id", "null")
        if search:
            query = query.or_(
                f"nombre.ilike.%{search}%,apellido.ilike.%{search}%"
            )

        result = _ordenado(query).range(start, end).execute()

        total = result.count if result.count is not None else 0
        return [row(r) for r in result.data], total

    # ── Lookups de una fila (delegados a _empleado_lookup_repo) ──

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[EmpleadoResponse]:
        """Busca por UUID validando empresa si se provee. Delegado a _empleado_lookup_repo.por_id."""
        return por_id(id, empresa_id)

    def find_by_legajo(self, legajo: str, empresa_id: UUID) -> Optional[EmpleadoResponse]:
        """Busca por legajo dentro de la empresa. Delegado a _empleado_lookup_repo.por_legajo."""
        return por_legajo(legajo, empresa_id)

    def find_by_dni(self, dni: str, empresa_id: UUID) -> Optional[EmpleadoResponse]:
        """Busca por DNI dentro de la empresa. Delegado a _empleado_lookup_repo.por_dni."""
        return por_dni(dni, empresa_id)

    # ── Escrituras (delegadas a _empleado_write_repo) ──

    def save(self, data: EmpleadoCreate, empresa_id: UUID) -> EmpleadoResponse:
        """Alta de empleado. Delegado a _empleado_write_repo.guardar."""
        return guardar(data, empresa_id)

    def update(self, id: str, data: EmpleadoUpdate, empresa_id: Optional[UUID] = None) -> Optional[EmpleadoResponse]:
        """Actualización parcial. Delegado a _empleado_write_repo.actualizar."""
        return actualizar(id, data, empresa_id, self.find_by_id)

    def dar_de_baja(self, empleado_id: str, fecha_egreso: date, empresa_id: Optional[UUID] = None) -> bool:
        """Baja con fecha de egreso. Delegado a _empleado_write_repo.dar_de_baja."""
        return dar_de_baja(empleado_id, fecha_egreso, empresa_id)
