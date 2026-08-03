"""
Reporte de distribución de la plantilla ACTIVA por seniority, modalidad de contratación y turno.
Es un corte transversal (snapshot al momento, sin período). Los valores nulos/vacíos se agrupan
en la categoría visible "Sin especificar" (no se descartan, no rompen) y quedan al final del ranking.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services._nomina_parsers import VACIOS
from services.reportes._common import _eid

_SIN = "Sin especificar"


def _agrupar(rows: List[dict], campo: str) -> List[dict]:
    """Cuenta por `campo`; los nulos/vacíos caen en 'Sin especificar'. Orden: por total desc,
    con 'Sin especificar' siempre al final.

    🔴 "VACÍO" NO ES SOLO NULL Y '': la lista canónica es `_nomina_parsers.VACIOS` y se IMPORTA,
    no se reescribe acá. El import ya la aplica al ESCRIBIR; esto la aplica al LEER, que es lo
    que cubre las filas cargadas ANTES de que un literal entrara a esa lista. Concreto: los 4
    empleados con `seniority = 'SIN DATOS'` de producción se cargaron cuando ese texto todavía
    no estaba en `VACIOS`, así que ya están en la base y ninguna corrección del import los toca.

    ⚠️ Esto agrupa BIEN pero NO limpia el dato: la columna sigue diciendo 'SIN DATOS' y cualquier
    otra superficie que la lea sin pasar por acá (el export de empleados, la ficha, un filtro
    futuro) lo va a seguir mostrando. Cerrar eso es un UPDATE, y es una decisión aparte."""
    conteo: dict[str, int] = {}
    for r in rows:
        valor = r.get(campo)
        crudo = valor.strip() if isinstance(valor, str) else valor
        clave = _SIN if not crudo or str(crudo).upper() in VACIOS else crudo
        conteo[clave] = conteo.get(clave, 0) + 1
    return sorted(
        [{"categoria": k, "total": v} for k, v in conteo.items()],
        key=lambda x: (x["categoria"] == _SIN, -x["total"]),
    )


def generate_distribucion(empresa_id: Optional[UUID] = None,
                          area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Distribución de la plantilla activa por seniority / tipo_contrato / turno.
    Filtra por empresa_id y/o area_id (empleados.area_id, directo).

    🔴 `por_modalidad` sale de `tipo_contrato`, NO de la ex `modalidad_contratacion`. Esta
    consulta leía esa otra columna, que ningún camino escribía: el reporte mostraba
    "Sin especificar" para toda la plantilla teniendo el dato en la columna de al lado (el
    import lo escribe en `tipo_contrato` desde la migración 065). La columna duplicada se borró
    en la 084; el porqué completo está ahí. La clave de salida sigue llamándose
    `por_modalidad` porque es lo que el front y el PDF ya consumen."""
    eid = _eid(empresa_id)
    aid = _eid(area_id)
    q = supabase_admin.table("empleados").select("seniority, tipo_contrato, turno").eq("estado", "activo")
    if eid:
        q = q.eq("empresa_id", eid)
    if aid:
        q = q.eq("area_id", aid)
    rows = q.execute().data or []

    return {
        "titulo": "Distribución de plantilla",
        "total_empleados": len(rows),
        "por_seniority": _agrupar(rows, "seniority"),
        "por_modalidad": _agrupar(rows, "tipo_contrato"),
        "por_turno": _agrupar(rows, "turno"),
    }
