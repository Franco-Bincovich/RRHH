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
from repositories._nomina_evolucion import evolucion
from repositories._nomina_row import SELECT as _NOM_SEL
from repositories._nomina_row import TABLE as _NOM
from repositories._nomina_row import item as _a_item
from repositories._nomina_row import row as _to_nomina
from schemas.costo import EvolucionMes, HistorialSalarialItem, NominaCreate, NominaResponse
from utils.errors import AppError


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
        empleado_id = str(data.empleado_id)  # UUID → str: sale a PostgREST en el .eq() Y en el payload
        emp_res = (
            supabase_admin.table("empleados")
            .select("empresa_id")
            .eq("id", empleado_id)
            .maybe_single()
            .execute()
        )
        if not emp_res.data or not emp_res.data.get("empresa_id"):
            raise AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
        cargas = max(0.0, data.monto_bruto - data.monto_neto)
        payload = {
            "empleado_id": empleado_id, "mes": data.mes, "anio": data.anio,
            "salario_bruto": data.monto_bruto, "cargas_sociales": cargas,
            "empresa_id": str(emp_res.data["empresa_id"]),
        }
        upsert_res = supabase_admin.table(_NOM).upsert(payload, on_conflict="empleado_id,anio,mes").execute()
        row_res = (
            supabase_admin.table(_NOM).select(_NOM_SEL)
            .eq("id", upsert_res.data[0]["id"]).single().execute()
        )
        return _to_nomina(row_res.data)

    def periodos_cargados(self, empresa_id: str) -> set[tuple]:
        """Conjunto de (empleado_id, anio, mes) ya registrados en la empresa.

        Lo usa el PREVIEW del import de nómina para marcar `es_actualizacion`. Vivía en
        `nomina_csv_service` como query suelta: es la única tabla de este repo y no tenía por
        qué resolverla el service.
        """
        res = supabase_admin.table(_NOM).select("empleado_id,anio,mes").eq("empresa_id", empresa_id).execute()
        return {(r["empleado_id"], int(r["anio"]), int(r["mes"])) for r in (res.data or [])}

    def get_evolucion(self, mes: int, anio: int, empresa_id: Optional[UUID] = None) -> List[EvolucionMes]:
        """Evolución de costos de los últimos 12 meses. Delegado a `_nomina_evolucion.evolucion`."""
        return evolucion(mes, anio, empresa_id)
