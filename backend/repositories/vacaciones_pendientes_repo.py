"""
Repositorio de días de vacaciones pendientes (service_key; control app-level).
Interfaz: find_all · find_by_id · crear · update · delete.

Reusa `enriquecer` de _vacaciones_utils (empresa/empleado/área por lookup batch, sin N+1):
esta tabla cuelga de un empleado igual que solicitudes_vacaciones y muestra los mismos
derivados, así que no se reimplementa la resolución.

🔴 FORMA A: el filtro de empresa va SIEMPRE en el WHERE de la query, nunca comparado después
en el service. Una sola ida a la base e imposible de saltear.
"""
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._vacaciones_utils import enriquecer
from schemas.vacaciones_pendientes import VacacionPendienteResponse
from utils.errors import AppError
from utils.logger import logger

_T = "vacaciones_pendientes"


def _row(r: dict) -> VacacionPendienteResponse:
    return VacacionPendienteResponse.model_validate(enriquecer([r])[0])


class VacacionesPendientesRepo:
    def find_all(self, empresa_id: Optional[UUID] = None, empleado_ids: Optional[List[str]] = None,
                 page: int = 1, page_size: int = 20,
                 ) -> Tuple[List[VacacionPendienteResponse], int]:
        """Página filtrada por empresa/empleado_ids + total real del filtro (count exacto).

        empleado_ids=None → sin filtro por empleado; la intersección ownership∩área∩proyecto la
        arma el service vía _ownership_filter. Los dos ejes conviven: el de empresa NO se
        reemplaza por el de ownership.
        """
        # `.order("id")` = desempate: `periodo` es un AÑO, asi que empatan casi todas las filas
        # entre si. Es el caso mas extremo de los siete listados paginados — sin el `id`, el orden
        # dentro de un periodo es el que Postgres quiera y cambia entre paginas.
        q = supabase_admin.table(_T).select("*", count="exact").order("periodo", desc=True).order("id")
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        if empleado_ids is not None:
            q = q.in_("empleado_id", empleado_ids)
        res = q.range((page - 1) * page_size, page * page_size - 1).execute()
        filas = enriquecer(res.data or [])
        return [VacacionPendienteResponse.model_validate(f) for f in filas], res.count or 0

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[VacacionPendienteResponse]:
        """Busca por UUID. Si empresa_id se provee, valida pertenencia EN LA QUERY (Forma A)."""
        q = supabase_admin.table(_T).select("*").eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.maybe_single().execute()
        return _row(res.data) if res and res.data else None

    def find_by_empleado(self, empleado_id: str, empresa_id: Optional[UUID] = None) -> List[VacacionPendienteResponse]:
        """Pendientes de un empleado, del período más reciente al más viejo."""
        q = supabase_admin.table(_T).select("*").eq("empleado_id", empleado_id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.order("periodo", desc=True).execute()
        return [VacacionPendienteResponse.model_validate(f) for f in enriquecer(res.data or [] if res else [])]

    def crear(self, datos: dict) -> VacacionPendienteResponse:
        """Inserta un registro de días pendientes y devuelve el creado (enriquecido)."""
        res = supabase_admin.table(_T).insert(datos).execute()
        if not res or not res.data:
            logger.error("Supabase insert vacío en vacaciones_pendientes")
            raise AppError("Error al registrar los días pendientes", "DB_ERROR", 500)
        return _row(res.data[0])

    def update(self, id: str, patch: dict, empresa_id: Optional[UUID] = None) -> Optional[VacacionPendienteResponse]:
        """Actualiza los campos provistos, con la empresa EN EL WHERE. Patch vacío → devuelve la fila."""
        if not patch:
            return self.find_by_id(id, empresa_id)
        q = supabase_admin.table(_T).update(patch).eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.execute()
        return _row(res.data[0]) if res and res.data else None

    def delete(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        """Borra el registro (hard delete), con la empresa EN EL WHERE. True si borró."""
        q = supabase_admin.table(_T).delete().eq("id", id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.execute()
        return bool(res and res.data)
