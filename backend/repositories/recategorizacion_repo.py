"""
Repositorio de recategorizaciones (migraciones 113/116/117). Acceso con supabase_admin.

Está partido en cuatro y la clase delega, así que sigue siendo la única puerta del service:
escrituras en `_recategorizacion_write_repo.py` · mapper en `_recategorizacion_row.py` · y las
dos consultas de las reglas de fecha retroactiva en `_recategorizacion_cadena.py`. Acá quedan
las DOS VISTAS y el `find_by_id`.

🔴 SÍ HAY BARRERA DE EMPRESA, al revés que `perfiles_puesto`. `recategorizaciones.empresa_id` es
NOT NULL y hay FK compuesta `(empleado_id, empresa_id) → empleados(id, empresa_id)`: una
recategorización pertenece a una sociedad concreta. `empresa_id=None` = vista consolidada y no
restringe (semántica de `get_empresa_id`), que NO es un fallo de validación.

DOS VISTAS DE LA MISMA TABLA, con formas distintas a propósito:
  · `find_all` → la planilla. PAGINADA, por `fecha_efectiva DESC`, con filtros.
  · `find_by_empleado` → el historial de la ficha. LISTA PLANA, sin paginar: son una o dos por
    persona por año y paginar sería un paginador de una página. Molde:
    `nomina_repo.find_by_empleado`, que alimenta el historial salarial de esa misma ficha.
Las dos ya tienen su índice desde la migración 113 (`idx_recat_empresa_fecha` e
`idx_recat_empleado`, los dos `(…, fecha_efectiva DESC)`).

🔴 NO HAY `delete`, y no es un olvido: se puede editar, no borrar. Borrar rompe el histórico y
la cadena de `*_anterior` que cuelga de él. Ver `schemas/recategorizacion.py`.
"""
from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._recategorizacion_cadena import previa as cadena_previa
from repositories._recategorizacion_cadena import ultima as cadena_ultima
from repositories._recategorizacion_row import SELECT, TABLE, build
from repositories._recategorizacion_write_repo import actualizar, guardar
from schemas.recategorizacion import (
    RecategorizacionCreate, RecategorizacionResponse, RecategorizacionUpdate,
)


def _con_empresa(q, empresa_id: Optional[UUID]):
    """Aplica el filtro de empresa si viene. None = consolidado, no restringe."""
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


class RecategorizacionRepo:
    def find_all(self, page: int = 1, page_size: int = 20,
                 empresa_id: Optional[UUID] = None, empleado_id: Optional[UUID] = None,
                 fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None,
                 ) -> Tuple[List[RecategorizacionResponse], int]:
        """Página de la planilla + el total REAL del filtro (sin paginar).

        El rango va sobre `fecha_efectiva` —cuándo RIGIÓ— y no sobre `created_at` —cuándo se
        cargó—. Con fecha retroactiva las dos difieren, y la pregunta de RRHH ("qué cambió en
        agosto") es siempre la primera.
        """
        q = _con_empresa(supabase_admin.table(TABLE).select(SELECT, count="exact"), empresa_id)
        if empleado_id:
            q = q.eq("empleado_id", str(empleado_id))
        if fecha_desde:
            q = q.gte("fecha_efectiva", str(fecha_desde))
        if fecha_hasta:
            q = q.lte("fecha_efectiva", str(fecha_hasta))
        res = (q.order("fecha_efectiva", desc=True)
                .range((page - 1) * page_size, page * page_size - 1).execute())
        return build(res.data or []), (res.count or 0)

    def find_by_id(self, id: str,
                   empresa_id: Optional[UUID] = None) -> Optional[RecategorizacionResponse]:
        """Una recategorización, o None si no existe o es de otra empresa."""
        q = _con_empresa(supabase_admin.table(TABLE).select(SELECT).eq("id", id), empresa_id)
        filas = build(q.limit(1).execute().data or [])
        return filas[0] if filas else None

    def find_by_empleado(self, empleado_id: str, empresa_id: Optional[UUID] = None,
                         ) -> List[RecategorizacionResponse]:
        """Historial completo de una persona, del más reciente al más viejo. Sin paginar."""
        q = _con_empresa(
            supabase_admin.table(TABLE).select(SELECT).eq("empleado_id", empleado_id), empresa_id)
        return build(q.order("fecha_efectiva", desc=True).execute().data or [])

    def find_previa(self, empleado_id: str, fecha: date,
                    excepto_id: Optional[str] = None) -> Optional[RecategorizacionResponse]:
        """La última recategorización ANTERIOR a `fecha`. Delega en `_recategorizacion_cadena`."""
        return cadena_previa(empleado_id, fecha, excepto_id)

    def find_ultima(self, empleado_id: str,
                    excepto_id: Optional[str] = None) -> Optional[RecategorizacionResponse]:
        """La de fecha efectiva MÁS ALTA de esa persona. Delega en `_recategorizacion_cadena`."""
        return cadena_ultima(empleado_id, excepto_id)

    def save(self, data: RecategorizacionCreate, empresa_id: UUID, anteriores: dict,
             fecha: date, registrado_por: Optional[str]) -> RecategorizacionResponse:
        """Alta. Delega en `_recategorizacion_write_repo.guardar`."""
        return guardar(data, empresa_id, anteriores, fecha, registrado_por)

    def update(self, id: str, data: RecategorizacionUpdate, anteriores: dict,
               ) -> Optional[RecategorizacionResponse]:
        """Edición parcial. Escribe y devuelve la fila resultante (o None si no existe)."""
        actualizar(id, data, anteriores)
        return self.find_by_id(id)
