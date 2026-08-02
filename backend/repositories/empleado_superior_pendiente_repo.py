"""
Repositorio de superiores pendientes de resolver (migración 086).

Guarda el nombre del jefe que el import de nómina leyó del CSV y no pudo resolver a un
`manager_id`. Estado TRANSITORIO: la fila se borra cuando se resuelve, así que en estado sano
esta tabla tiene CERO filas — por eso el listado no se pagina.

🔴 EL LISTADO NO ACOTA POR EMPRESA CUANDO `empresa_id` ES None (vista consolidada), igual que el
resto de los listados. Pero ojo con la asimetría: el `empresa_id` de la fila es el DEL EMPLEADO,
no el del superior (que es lo que no se sabe). Scopear el listado por empresa es correcto —lo que
se lista son empleados—; scopear la BÚSQUEDA del superior por empresa NO lo sería, y esa búsqueda
no vive acá sino en `_empleado_lookup_repo.indice_por_nombre`, que a propósito no acota.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin

_TABLE = "empleado_superior_pendiente"
# El nombre del empleado se resuelve por embed y no se guarda duplicado: es un dato derivado, y
# guardarlo dejaría el pendiente mostrando un nombre viejo si al empleado lo renombran.
_SELECT = "empleado_id, empresa_id, apellido_csv, nombre_csv, motivo, created_at, empleados!empleado_superior_pendiente_empleado_id_fkey(nombre, apellido)"


class EmpleadoSuperiorPendienteRepo:
    def upsert_muchos(self, filas: List[dict]) -> int:
        """Inserta o pisa los pendientes. PK = empleado_id → un re-import ACTUALIZA, no duplica.

        Args:
            filas: dicts con empleado_id, empresa_id, apellido_csv, nombre_csv, motivo.

        Returns:
            Cuántas filas quedaron escritas.
        """
        if not filas:
            return 0
        res = supabase_admin.table(_TABLE).upsert(filas, on_conflict="empleado_id").execute()
        return len(res.data or [])

    def borrar_muchos(self, empleado_ids: List[str]) -> int:
        """Borra los pendientes de esos empleados (se resolvieron). [] → no consulta."""
        if not empleado_ids:
            return 0
        res = supabase_admin.table(_TABLE).delete().in_("empleado_id", empleado_ids).execute()
        return len(res.data or [])

    def listar(self, empresa_id: Optional[UUID] = None) -> List[dict]:
        """Todos los pendientes, con el nombre del empleado resuelto por embed.

        Sin paginar a propósito: en estado sano son 0 filas y en el peor caso son los empleados
        de un import cuyo jefe no estaba cargado. Si algún día esto necesitara paginarse, sería
        señal de que el flujo de alta de jefes está roto, no de que falta paginación.
        """
        q = supabase_admin.table(_TABLE).select(_SELECT).order("created_at")
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return q.execute().data or []
