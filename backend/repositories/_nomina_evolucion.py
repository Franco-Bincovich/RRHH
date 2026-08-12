"""
Evolución de costos de los últimos 12 meses. Satélite de `nomina_repo.py`.

Se extrajo porque `nomina_repo` estaba en **99/100** y no admitía el método que faltaba
(`periodos_cargados`, el lookup que el import de nómina hacía por su cuenta). Molde:
`_empleado_write_repo.py` — función libre, y el repo delega en una línea.

El corte cayó acá y no en otro método por una costura que ya existía: es el único bloque del
repo que **no devuelve filas de nómina**, sino una serie agregada, y se lleva con él su único
helper (`_prev_period`). Los otros tres métodos son lecturas/escrituras sobre la misma tabla y
el mismo mapper: partirlos dejaría dos archivos hablando de lo mismo.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._nomina_row import TABLE as _NOM
from schemas.costo import EvolucionMes


def _prev_period(mes: int, anio: int) -> tuple[int, int]:
    return (mes - 1, anio) if mes > 1 else (12, anio - 1)


def evolucion(mes: int, anio: int, empresa_id: Optional[UUID] = None) -> List[EvolucionMes]:
    """
    Evolución de costos de los últimos 12 meses.
    CRÍTICO: filtra por empresa_id cuando se provee — no mezcla empresas en el SUM.
    """
    periodos: list[tuple[int, int]] = []
    m, y = mes, anio
    for _ in range(12):
        periodos.append((m, y))
        m, y = _prev_period(m, y)
    min_y = min(y for _, y in periodos)
    q = (
        supabase_admin.table(_NOM).select("mes,anio,total")
        .gte("anio", min_y).lte("anio", anio)
    )
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    res = q.execute()
    ps = set(periodos)
    totals: dict[tuple[int, int], float] = {}
    for r in (res.data or []):
        k = (int(r["mes"]), int(r["anio"]))
        if k in ps:
            totals[k] = totals.get(k, 0.0) + float(r.get("total") or 0)
    return [
        EvolucionMes(mes=m, anio=y, total=round(totals[(m, y)], 2))
        for m, y in reversed(periodos)
        if (m, y) in totals
    ]
