"""
R10 — Ausentismo por área. Por cada área, días totales y días injustificados del período, más
sus tasas % sobre una base de días hábiles/mes/empleado (headcount del área como denominador).
El área vive en empleados → filtro de área por JOIN inner por empleado. El parámetro `vista`
(total | injustificado | ambos, default ambos) decide qué columnas de métrica salen.
La nota del cálculo va como escalar en `datos` → sale visible en el "Resumen" de PDF/Excel.

🔴 LA BASE DE DÍAS HÁBILES YA NO ES UNA CONSTANTE: sale de parametros_empresa (migración 085),
resuelta por COALESCE(mi empresa, global). Antes era `_BASE_DIAS_HABILES = 22` acá y el "22"
estaba TIPEADO ADEMÁS dentro del texto de la nota, así que cambiarlo en un lugar y no en el
otro dejaba el reporte diciendo una base y calculando con otra. Ahora la nota se construye
CON el mismo número que se usó para dividir: `nota(base)` recibe lo mismo que `_tasa`, y no
hay forma de que discrepen sin que el compilador lo pida.

🔴 DOS FILTROS DISTINTOS SOBRE LO MISMO, no confundirlos:
  · `cuenta_ausentismo` (del TIPO) decide si la ausencia ENTRA en la cuenta. Es política.
  · `justificada` (de la AUSENCIA) parte lo que entró en total vs injustificado. Es un hecho.
Una licencia por maternidad puede estar justificada y aun así no computar como ausentismo.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services.configuracion_service import ConfiguracionService
from services.reportes._common import EMBED_AREA_DE_EMPLEADO as _AREA
from services.reportes._common import _eid, periodo_str, rango_mes


def base_dias_habiles(empresa_id: Optional[UUID] = None) -> int:
    """Días hábiles/mes/empleado configurados para la empresa (o los globales)."""
    return ConfiguracionService().get_parametros(empresa_id).base_dias_habiles


def nota(base: int) -> str:
    """
    El texto que explica el cálculo, construido CON la base usada.

    Es función y no constante justamente por eso: como constante, el número quedaba tipeado
    dentro del string y podía divergir del que dividía en silencio.
    """
    return f"Las tasas se calculan sobre una base de {base} días hábiles por mes por colaborador."


def _tasa(dias: int, headcount: int, base_dias: int) -> float:
    """% de ausentismo. `base_dias` es obligatorio a propósito: sin default no se puede llamar
    con la base equivocada por olvido."""
    base = base_dias * headcount
    return round(dias / base * 100, 2) if base > 0 else 0.0


def generate_ausentismo(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                        area_id: Optional[UUID] = None, vista: str = "ambos") -> Dict[str, Any]:
    """Ausentismo por área (días totales/injustificados + tasas). Filtra por empresa_id y/o
    area_id (join inner por empleado en las ausencias; directo en el headcount del denominador).
    La base de días hábiles sale de la configuración de la empresa (migración 085)."""
    ini, fin = rango_mes(mes, anio)
    eid, aid = _eid(empresa_id), _eid(area_id)
    base = base_dias_habiles(empresa_id)
    db = supabase_admin

    # Denominador: headcount de activos por área.
    # `areas` se alcanza nombrando la FK: hay DOS relaciones entre empleados y areas
    # (empleados.area_id y areas.responsable_id), y sin el hint PostgREST devuelve PGRST201.
    emp_q = db.table("empleados").select(f"area_id, {_AREA}").eq("estado", "activo")
    if eid:
        emp_q = emp_q.eq("empresa_id", eid)
    if aid:
        emp_q = emp_q.eq("area_id", aid)
    headcount: dict[str, int] = {}
    for e in (emp_q.execute().data or []):
        nombre = (e.get("areas") or {}).get("nombre") or "Sin área"
        headcount[nombre] = headcount.get(nombre, 0) + 1

    # `tipos_ausencia(cuenta_ausentismo)` NO necesita hint de FK: entre solicitudes_ausencia y
    # tipos_ausencia hay UNA sola relación (tipo_id), así que no hay ambigüedad que resolver.
    _TIPO = "tipos_ausencia(cuenta_ausentismo)"
    aus_sel = (f"dias, justificada, {_TIPO}, empleados!inner({_AREA})" if aid
               else f"dias, justificada, {_TIPO}, empleados({_AREA})")
    aus_q = (db.table("solicitudes_ausencia").select(aus_sel)
             .gte("fecha_desde", ini).lte("fecha_desde", fin))
    if eid:
        aus_q = aus_q.eq("empresa_id", eid)
    if aid:
        aus_q = aus_q.eq("empleados.area_id", aid)
    totales: dict[str, int] = {}
    injust: dict[str, int] = {}
    for a in (aus_q.execute().data or []):
        # Sin fila de tipo (dato viejo o embed no resuelto) se CUENTA: es el comportamiento
        # previo a la 085 y el default de la columna. Descartar por defecto haría desaparecer
        # ausencias reales de la tasa sin que nadie lo pida.
        tipo = a.get("tipos_ausencia") or {}
        if tipo.get("cuenta_ausentismo") is False:
            continue
        nombre = ((a.get("empleados") or {}).get("areas") or {}).get("nombre") or "Sin área"
        d = int(a.get("dias") or 0)
        totales[nombre] = totales.get(nombre, 0) + d
        if not a.get("justificada"):
            injust[nombre] = injust.get(nombre, 0) + d

    ver_total = vista in ("total", "ambos")
    ver_injust = vista in ("injustificado", "ambos")
    filas = []
    for nombre in sorted(set(headcount) | set(totales)):
        hc = headcount.get(nombre, 0)
        fila: Dict[str, Any] = {"area": nombre, "headcount": hc}
        if ver_total:
            fila["dias_totales"] = totales.get(nombre, 0)
            fila["tasa_total_pct"] = _tasa(totales.get(nombre, 0), hc, base)
        if ver_injust:
            fila["dias_injustificados"] = injust.get(nombre, 0)
            fila["tasa_injustificada_pct"] = _tasa(injust.get(nombre, 0), hc, base)
        filas.append(fila)

    orden = "dias_totales" if ver_total else "dias_injustificados"
    return {
        "titulo": f"Ausentismo por área — {periodo_str(mes, anio)}",
        "periodo": {"mes": mes, "anio": anio},
        "nota": nota(base),
        "ausentismo": sorted(filas, key=lambda x: x.get(orden, 0), reverse=True),
    }
