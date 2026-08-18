"""
Reporte de altas y bajas del período: LISTADO NOMINAL de ingresos y egresos (no solo conteos).
- Altas: fecha_ingreso dentro del período, EXCLUYENDO preingresos (todavía no entraron).
- Bajas: fecha_egreso dentro del período Y `estado = 'baja'` (incluye motivo_baja; el rango ya
  excluye los null por sí solo, pero una fecha cargada no alcanza para ser una baja).
Con 0 movimientos las listas salen vacías y los totales en 0 (empty state coherente, no error).
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.reportes._common import EMBED_AREA_DE_EMPLEADO as _AREA_EMBED
from services.reportes._common import _eid, periodo_str, rango_mes
from utils.estados_empleado import ESTADO_PREINGRESO


def _nombre(r: dict) -> str:
    return f"{r.get('apellido', '')}, {r.get('nombre', '')}".strip(", ").strip()


def _area(r: dict) -> str:
    return (r.get("areas") or {}).get("nombre") or "Sin área"


def generate_altas_bajas(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                         area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Listado nominal de altas (por fecha_ingreso) y bajas (por fecha_egreso) del período.
    Filtra por empresa_id y/o area_id (empleados.area_id, directo)."""
    ini, fin = rango_mes(mes, anio)
    eid = _eid(empresa_id)
    aid = _eid(area_id)
    db = supabase_admin

    # 🔴 EXCLUYE PREINGRESOS, por COMPLEMENTO y no enumerando los estados en plantilla: quien
    # entró en marzo y se fue en julio sigue siendo un alta de marzo, así que `baja` queda del
    # lado que cuenta (ver `utils/estados_empleado.py`).
    # Acá el filtro pesa más que en los contadores hermanos: esto no es un número agregado sino
    # un LISTADO NOMINAL, así que sin el filtro salía el nombre y apellido de alguien que todavía
    # no entró, en un PDF que RRHH manda.
    altas_q = (db.table("empleados").select(f"nombre, apellido, fecha_ingreso, {_AREA_EMBED}")
               .neq("estado", ESTADO_PREINGRESO)
               .gte("fecha_ingreso", ini).lte("fecha_ingreso", fin).order("fecha_ingreso"))
    if eid:
        altas_q = altas_q.eq("empresa_id", eid)
    if aid:
        altas_q = altas_q.eq("area_id", aid)
    altas: List[dict] = [
        {"empleado": _nombre(r), "area": _area(r), "fecha_ingreso": str(r.get("fecha_ingreso") or "")}
        for r in (altas_q.execute().data or [])
    ]

    # fecha_egreso es nullable; el rango gte/lte ya excluye los null (un null no matchea >= ini).
    # 🔴 `.eq("estado", "baja")` — ES UN FILTRO QUE FALTABA, no uno nuevo. Sus DOS hermanos ya lo
    # tenían (`dashboard_service._calcular_kpis` y `_reporte_dotacion.generate_headcount`), así
    # que las bajas se contaban con dos criterios distintos según el reporte que abrieras.
    # Sin él alcanza con que alguien tenga `fecha_egreso` cargada para figurar como baja del mes:
    # el caso vivo es un preingreso que se cae ANTES de entrar y al que le cargan la fecha —
    # aparecería como una rotación que nunca ocurrió—, pero el agujero es más amplio que eso y no
    # depende de la migración 120. Acá va la ENUMERACIÓN y no el complemento, al revés que en las
    # altas, porque la pregunta es la contraria: no "¿esto ocurrió?" sino "¿esta persona se fue?".
    bajas_q = (db.table("empleados").select(f"nombre, apellido, fecha_egreso, motivo_baja, {_AREA_EMBED}")
               .eq("estado", "baja")
               .gte("fecha_egreso", ini).lte("fecha_egreso", fin).order("fecha_egreso"))
    if eid:
        bajas_q = bajas_q.eq("empresa_id", eid)
    if aid:
        bajas_q = bajas_q.eq("area_id", aid)
    bajas: List[dict] = [
        {"empleado": _nombre(r), "area": _area(r), "fecha_egreso": str(r.get("fecha_egreso") or ""),
         "motivo": r.get("motivo_baja") or "Sin especificar"}
        for r in (bajas_q.execute().data or [])
    ]

    return {
        "titulo": f"Altas y bajas — {periodo_str(mes, anio)}",
        "periodo": {"mes": mes, "anio": anio},
        "total_altas": len(altas),
        "total_bajas": len(bajas),
        "altas": altas,
        "bajas": bajas,
    }
