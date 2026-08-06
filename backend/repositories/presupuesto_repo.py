"""
Repositorio de presupuesto de áreas (presupuesto_areas). Acceso a Supabase con supabase_admin.
Interfaz pública: get_presupuesto_area · save_presupuesto · get_presupuestos_mes
empresa_id en escritura se hereda automáticamente del área (no se solicita explícito).
Todas las lecturas filtran por empresa_id cuando se provee.
"""
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.costo import PresupuestoCreate, PresupuestoResponse
from utils.errors import AppError

_PRE = "presupuesto_areas"
_PRE_SEL = "id,area_id,empresa_id,mes,anio,monto_presupuestado,areas!presupuesto_areas_area_emp_fkey(nombre)"


def _to_presupuesto(r: dict) -> PresupuestoResponse:
    area = r.get("areas") or {}
    emp = r.get("empresa_id")
    return PresupuestoResponse(
        id=str(r["id"]), area_id=str(r["area_id"]),
        area_nombre=area.get("nombre", ""),
        # _PRE_SEL ya la traía; el mapper la descartaba, así que el dato llegaba a la base y se
        # perdía al volver. La necesita el evento de auditoría (empresa DEL REGISTRO, no del header).
        empresa_id=str(emp) if emp else None,
        mes=int(r["mes"]), anio=int(r["anio"]),
        presupuesto=float(r["monto_presupuestado"]),
    )


class PresupuestoRepo:
    def get_presupuesto_area(self, area_id: str, mes: int, anio: int, empresa_id: Optional[UUID] = None) -> Optional[PresupuestoResponse]:
        """Retorna el presupuesto de un área para el período. Filtra por empresa si se provee."""
        q = (
            supabase_admin.table(_PRE).select(_PRE_SEL)
            .eq("area_id", area_id).eq("mes", mes).eq("anio", anio).eq("tipo_costo", "nomina")
        )
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.execute()
        return _to_presupuesto(res.data[0]) if res.data else None

    def save_presupuesto(self, data: PresupuestoCreate) -> PresupuestoResponse:
        """Upsert de presupuesto. empresa_id se hereda del área (FK compuesta garantiza coherencia)."""
        area_res = (
            supabase_admin.table("areas")
            .select("empresa_id")
            .eq("id", data.area_id)
            .maybe_single()
            .execute()
        )
        if not area_res.data or not area_res.data.get("empresa_id"):
            raise AppError("Área no encontrada", "AREA_NOT_FOUND", 404)
        payload = {
            "area_id": data.area_id, "mes": data.mes, "anio": data.anio,
            "monto_presupuestado": data.presupuesto, "tipo_costo": "nomina",
            "empresa_id": str(area_res.data["empresa_id"]),
        }
        supabase_admin.table(_PRE).upsert(payload, on_conflict="area_id,anio,mes,tipo_costo").execute()
        return self.get_presupuesto_area(data.area_id, data.mes, data.anio)  # type: ignore[return-value]

    def get_presupuestos_mes(self, mes: int, anio: int, empresa_id: Optional[UUID] = None) -> dict[tuple[str, str], float]:
        """
        Retorna presupuestos del período por clave (empresa_id, area_nombre).
        CRÍTICO: filtra por empresa_id cuando se provee — no mezcla empresas.
        Clave compuesta evita colisión si dos empresas tienen áreas con el mismo nombre.
        """
        q = (
            supabase_admin.table(_PRE)
            .select("empresa_id,monto_presupuestado,areas!presupuesto_areas_area_emp_fkey(nombre)")
            .eq("mes", mes).eq("anio", anio).eq("tipo_costo", "nomina")
        )
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        res = q.execute()
        return {
            (str(p.get("empresa_id", "")), (p.get("areas") or {}).get("nombre", "")): float(p["monto_presupuestado"])
            for p in (res.data or [])
            if (p.get("areas") or {}).get("nombre")
        }
