"""
Reporte de distribución de la plantilla ACTIVA por seniority, modalidad de contratación y turno.
Es un corte transversal (snapshot al momento, sin período). Los valores nulos/vacíos se agrupan
en la categoría visible "Sin especificar" (no se descartan, no rompen) y quedan al final del ranking.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.reportes._common import _eid

_SIN = "Sin especificar"


def _agrupar(rows: List[dict], campo: str) -> List[dict]:
    """Cuenta por `campo`; los nulos/vacíos caen en 'Sin especificar'. Orden: por total desc,
    con 'Sin especificar' siempre al final."""
    conteo: dict[str, int] = {}
    for r in rows:
        valor = r.get(campo)
        clave = (valor or "").strip() if isinstance(valor, str) else (valor or _SIN)
        clave = clave or _SIN
        conteo[clave] = conteo.get(clave, 0) + 1
    return sorted(
        [{"categoria": k, "total": v} for k, v in conteo.items()],
        key=lambda x: (x["categoria"] == _SIN, -x["total"]),
    )


def generate_distribucion(empresa_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Distribución de la plantilla activa por seniority / modalidad_contratacion / turno.
    Filtra por empresa_id si se provee."""
    eid = _eid(empresa_id)
    q = supabase_admin.table("empleados").select("seniority, modalidad_contratacion, turno").eq("estado", "activo")
    if eid:
        q = q.eq("empresa_id", eid)
    rows = q.execute().data or []

    return {
        "titulo": "Distribución de plantilla",
        "total_empleados": len(rows),
        "por_seniority": _agrupar(rows, "seniority"),
        "por_modalidad": _agrupar(rows, "modalidad_contratacion"),
        "por_turno": _agrupar(rows, "turno"),
    }
