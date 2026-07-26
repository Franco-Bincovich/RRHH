"""
Repositorio de empleados — queries reales a Supabase.
Interfaz pública: find_all · find_by_id · save · update · soft_delete
Todas las operaciones reciben empresa_id para filtrado multiempresa.
"""
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoUpdate
from utils.errors import AppError
from utils.logger import logger

_TABLE = "empleados"

# Select con joins resueltos en una sola query (sin N+1): nombre de área, empresa y
# del manager. El manager es un self-join to-one: se embebe por la COLUMNA FK
# (manager:manager_id) en vez del nombre de la constraint — el hint por columna sigue la
# FK hacia empleados.id (dirección many-to-one correcta) y es inmune al nombre autogenerado
# de la constraint, que difiere entre entornos (era el origen del PGRST200 en /api/empleados).
_SELECT = (
    "*, areas!empleados_area_id_fkey(nombre), empresas(nombre), "
    "manager:manager_id(nombre, apellido)"
)


def _with_empresa(query, empresa_id: Optional[UUID]):
    """Aplica filtro de empresa a una query de Supabase si empresa_id no es None."""
    return query.eq("empresa_id", str(empresa_id)) if empresa_id else query


def _row(r: dict) -> EmpleadoResponse:
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
    ) -> Tuple[List[EmpleadoResponse], int]:
        """Retorna la página de empleados con area_nombre resuelto y el total sin paginar."""
        start = (page - 1) * page_size
        end = start + page_size - 1

        query = supabase_admin.table(_TABLE).select(_SELECT, count="exact")
        query = _with_empresa(query, empresa_id)

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
        return [_row(r) for r in result.data], total

    def find_by_id(self, id: str, empresa_id: Optional[UUID] = None) -> Optional[EmpleadoResponse]:
        """Busca un empleado por UUID. Si empresa_id se provee, valida pertenencia. Devuelve None si no existe o no pertenece."""
        query = _with_empresa(
            supabase_admin.table(_TABLE).select(_SELECT).eq("id", id),
            empresa_id,
        )
        result = query.maybe_single().execute()
        if not result or not result.data:
            return None
        return _row(result.data)

    def save(self, data: EmpleadoCreate, empresa_id: UUID) -> EmpleadoResponse:
        """Inserta un nuevo empleado en la empresa indicada y devuelve el registro creado."""
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        payload["area_id"] = str(data.area_id)
        payload["empresa_id"] = str(empresa_id)
        payload["fecha_ingreso"] = str(data.fecha_ingreso)
        if data.fecha_nacimiento:
            payload["fecha_nacimiento"] = str(data.fecha_nacimiento)
        if data.manager_id:
            payload["manager_id"] = str(data.manager_id)
        payload["estado"] = "activo"

        result = supabase_admin.table(_TABLE).insert(payload).execute()
        if not result.data:
            logger.error("Supabase insert vacío en empleados")
            raise AppError("Error al crear empleado", "DB_ERROR", 500)
        return _row(result.data[0])

    def update(self, id: str, data: EmpleadoUpdate, empresa_id: Optional[UUID] = None) -> Optional[EmpleadoResponse]:
        """Actualiza solo los campos no-None y devuelve el registro actualizado. Si empresa_id se provee, restringe el WHERE."""
        patch = {k: v for k, v in data.model_dump(exclude_none=True).items()}
        # manager_id: null explícito = limpiar (exclude_none lo descarta; exclude_unset lo detecta).
        if "manager_id" in data.model_dump(exclude_unset=True):
            patch["manager_id"] = str(data.manager_id) if data.manager_id else None
        if not patch:
            return self.find_by_id(id, empresa_id)
        if "area_id" in patch:
            patch["area_id"] = str(patch["area_id"])
        if "fecha_ingreso" in patch:
            patch["fecha_ingreso"] = str(patch["fecha_ingreso"])
        if "fecha_nacimiento" in patch and patch["fecha_nacimiento"]:
            patch["fecha_nacimiento"] = str(patch["fecha_nacimiento"])

        stmt = _with_empresa(supabase_admin.table(_TABLE).update(patch).eq("id", id), empresa_id)
        result = stmt.execute()
        if not result.data:
            return None
        return _row(result.data[0])

    def find_by_legajo(self, legajo: str, empresa_id: UUID) -> Optional[EmpleadoResponse]:
        """Busca un empleado por legajo dentro de la empresa. Devuelve None si no existe."""
        res = (supabase_admin.table(_TABLE)
               .select(_SELECT)
               .eq("legajo", legajo).eq("empresa_id", str(empresa_id))
               .maybe_single().execute())
        return _row(res.data) if res and res.data else None

    def find_by_dni(self, dni: str, empresa_id: UUID) -> Optional[EmpleadoResponse]:
        """Busca un empleado por DNI en la empresa indicada. Devuelve None si no existe."""
        res = supabase_admin.table(_TABLE).select(_SELECT).eq("dni", dni).eq("empresa_id", str(empresa_id)).maybe_single().execute()
        return _row(res.data) if res and res.data else None

    def soft_delete(self, id: str, empresa_id: Optional[UUID] = None) -> bool:
        """Marca el empleado como baja sin eliminar el registro. Si empresa_id se provee, restringe el WHERE."""
        stmt = _with_empresa(supabase_admin.table(_TABLE).update({"estado": "baja"}).eq("id", id), empresa_id)
        return bool(stmt.execute().data)

    def dar_de_baja(self, empleado_id: str, fecha_egreso: date, empresa_id: Optional[UUID] = None) -> bool:
        """Da de baja a un empleado: setea estado='baja' y fecha_egreso en un solo UPDATE.

        Usado al iniciar un offboarding. A diferencia de soft_delete, registra también
        la fecha de egreso, como exige MODELO_DATOS.md (baja = estado + fecha_egreso).

        Args:
            empleado_id: UUID (str) del empleado a dar de baja.
            fecha_egreso: fecha de egreso a registrar.
            empresa_id: si se provee, restringe el WHERE a esa empresa.

        Returns:
            True si se actualizó alguna fila; False si el empleado no existe o no pertenece a la empresa.
        """
        stmt = _with_empresa(
            supabase_admin.table(_TABLE)
            .update({"estado": "baja", "fecha_egreso": str(fecha_egreso)})
            .eq("id", empleado_id),
            empresa_id,
        )
        return bool(stmt.execute().data)
