"""
Repositorio de nómina (costos_nomina). Acceso a Supabase con supabase_admin.
La tabla, el SELECT con joins y el mapper de fila viven en _nomina_row.py.
Interfaz pública: get_nomina_mes · save_nomina · get_evolucion
empresa_id en escritura se hereda automáticamente del empleado (no se solicita explícito).
Todas las lecturas y el cálculo de evolución filtran por empresa_id cuando se provee.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._nomina_row import SELECT as _NOM_SEL
from repositories._nomina_row import TABLE as _NOM
from repositories._nomina_row import item as _a_item
from repositories._nomina_row import row as _to_nomina
from schemas.costo import EvolucionMes, HistorialSalarialItem, NominaCreate, NominaResponse
from utils.errors import AppError


def _prev_period(mes: int, anio: int) -> tuple[int, int]:
    return (mes - 1, anio) if mes > 1 else (12, anio - 1)


class NominaRepo:
    def get_nomina_mes(self, mes: int, anio: int, empresa_id: Optional[UUID] = None) -> List[NominaResponse]:
        """Retorna nómina del período. Si empresa_id se provee, filtra — sin mezclar empresas."""
        q = supabase_admin.table(_NOM).select(_NOM_SEL).eq("mes", mes).eq("anio", anio)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return [_to_nomina(r) for r in (q.execute().data or [])]

    def find_by_empleado(self, empleado_id: str, empresa_id: Optional[UUID] = None) -> List[HistorialSalarialItem]:
        """Serie salarial del empleado, del período más reciente al más viejo.

        Ordena por (anio, mes) en la query y no en Python: la serie es el producto, y un orden
        que dependa del orden de llegada de las filas se rompe en silencio.
        `UNIQUE (empleado_id, anio, mes)` garantiza que no haya dos filas del mismo período.
        """
        q = (supabase_admin.table(_NOM).select("anio,mes,salario_bruto,cargas_sociales")
             .eq("empleado_id", empleado_id)
             .order("anio", desc=True).order("mes", desc=True))
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return [_a_item(r) for r in (q.execute().data or [])]

    def save_nomina(self, data: NominaCreate) -> NominaResponse:
        """Upsert de nómina. empresa_id se hereda del empleado (FK compuesta garantiza coherencia)."""
        emp_res = (
            supabase_admin.table("empleados")
            .select("empresa_id")
            .eq("id", data.empleado_id)
            .maybe_single()
            .execute()
        )
        if not emp_res.data or not emp_res.data.get("empresa_id"):
            raise AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
        cargas = max(0.0, data.monto_bruto - data.monto_neto)
        payload = {
            "empleado_id": data.empleado_id, "mes": data.mes, "anio": data.anio,
            "salario_bruto": data.monto_bruto, "cargas_sociales": cargas,
            "empresa_id": str(emp_res.data["empresa_id"]),
        }
        upsert_res = supabase_admin.table(_NOM).upsert(payload, on_conflict="empleado_id,anio,mes").execute()
        row_res = (
            supabase_admin.table(_NOM).select(_NOM_SEL)
            .eq("id", upsert_res.data[0]["id"]).single().execute()
        )
        return _to_nomina(row_res.data)

    def get_evolucion(self, mes: int, anio: int, empresa_id: Optional[UUID] = None) -> List[EvolucionMes]:
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
