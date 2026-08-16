"""
Los dos lookups sobre `empleados` que el módulo de vacaciones necesita.

SALIERON DE `vacaciones_repo.py`, que estaba en 103/100 después de restaurar el comentario del
desempate. El corte no es por tamaño: **son las dos únicas funciones de ese repo que NO consultan
`solicitudes_vacaciones`.** Estaban ahí porque el módulo las usa, no porque sean lecturas de su
tabla — la misma línea que separó `_scope_filtros.py` del repo de empleados.

Las dos alimentan reglas de negocio del módulo, no la pantalla:
  · `empresa_de_empleado` → de qué empresa se hereda la solicitud al crearla (Vista vs Acción: la
    empresa de una vacación sale del EMPLEADO, nunca del header).
  · `datos_para_saldo`    → los tres campos que entran al cálculo del cupo de vacaciones.
"""
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin

_EMP = "empleados"


def empresa_de_empleado(empleado_id: str) -> Optional[str]:
    """Retorna el empresa_id del empleado, o None si no existe."""
    res = supabase_admin.table(_EMP).select("empresa_id").eq("id", empleado_id).maybe_single().execute()
    return str(res.data["empresa_id"]) if res.data else None


def datos_para_saldo(empleado_id: str, empresa_id: Optional[UUID] = None) -> Optional[dict]:
    """Los TRES campos del empleado que entran al cálculo del saldo, o None si no existe o
    es de otra empresa (empresa_id None = consolidado, no restringe).

    Reemplazó a `find_dias_asignados`, que traía una sola columna: desde que el cupo sale de
    la antigüedad, el saldo necesita además las dos fechas de ingreso. Se traen en la MISMA
    query a propósito — dos lecturas de la misma fila podrían caer a los dos lados de un
    UPDATE y calcular la antigüedad contra un override que ya no es el de esa fila.
    """
    q = (supabase_admin.table(_EMP)
         .select("fecha_ingreso, fecha_ingreso_reconocida, dias_vacaciones_asignados")
         .eq("id", empleado_id))
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    res = q.maybe_single().execute()
    return res.data if res.data else None
