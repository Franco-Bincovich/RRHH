"""
R11 saldos_vacaciones — saldo por empleado, con el MISMO núcleo que la pantalla de vacaciones.

Vivía en `_reporte_vacaciones.py` junto con R9. Se separó cuando ese archivo pasó el límite de
150 líneas: son dos reportes distintos que solo compartían tres formateadores, y los dos que
comparten de verdad (`_nombre`, `_area`) se mudaron a `_common.py`.

El área vive en empleados (las solicitudes no la tienen) → filtro de área por `empleados.area_id`
directo. Con tablas vacías la lista sale vacía y los totales en 0 (empty state, no error).
"""
from datetime import date
from typing import Any, Dict, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services._vacaciones_cupos import cupos_por_periodo
from services._vacaciones_fifo import Consumo, saldo
from services._vacaciones_saldo import periodos_a_calcular
from services.reportes._common import EMBED_AREA_DE_EMPLEADO as _AREA
from services.reportes._common import _area, _eid, _nombre, rango_mes


def _fecha(s) -> str:
    """ISO 'YYYY-MM-DD' → 'DD/MM/YYYY'. Solo para el título ("saldos al <fecha de corte>")."""
    p = str(s)[:10].split("-") if s else []
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else (str(s) if s else "")


def generate_saldos_vacaciones(mes: int, anio: int, empresa_id: Optional[UUID] = None,
                               area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """R11 — saldo de vacaciones por empleado activo, CON EL MISMO NÚCLEO que la pantalla.

    🚩 ESTE REPORTE CAMBIÓ DE SIGNIFICADO Y FALTA CONFIRMARLO CON RRHH.
    Antes su columna "tomados" era el CONSUMO DEL MES (filtraba `fecha_desde` dentro de
    [mes, año]) y lo restaba de un cupo ANUAL: restaba magnitudes distintas, así que la
    columna "saldo" no era ni el saldo ni el movimiento. Ahora `mes/anio` es una FECHA DE
    CORTE y el reporte responde "cuánto le queda a cada uno AL CIERRE DE ESE MES", que es lo
    mismo que muestra la pantalla de vacaciones. Si lo que RRHH necesitaba era el movimiento
    del mes, eso es OTRO reporte y hay que agregarlo — no volver a mezclar los dos.

    🔴 TRES QUERIES, NO N+1. El núcleo (`_vacaciones_cupos` / `_vacaciones_fifo`) es puro y no
    puede consultar nada, así que la única forma de alimentarlo para N empleados es en batch:
    una query de empleados, una de solicitudes y una de pendientes, y después Python. Es el
    mismo patrón que evitó reintroducir el N+1 que explotó en sucesión.
    """
    _, fin = rango_mes(mes, anio)
    corte = date.fromisoformat(fin)
    eid, aid = _eid(empresa_id), _eid(area_id)
    db = supabase_admin

    emp_q = (db.table("empleados")
             .select(f"id, nombre, apellido, fecha_ingreso, fecha_ingreso_reconocida, "
                     f"dias_vacaciones_asignados, {_AREA}")
             .eq("estado", "activo"))
    if eid:
        emp_q = emp_q.eq("empresa_id", eid)
    if aid:
        emp_q = emp_q.eq("area_id", aid)
    empleados = emp_q.execute().data or []
    ids = [e["id"] for e in empleados]

    por_empleado = _consumos_batch(db, ids, eid, corte) if ids else {}
    filas = [_fila_saldo(emp, por_empleado.get(emp["id"], []), corte) for emp in empleados]
    return {
        "titulo": f"Saldos de vacaciones al {_fecha(fin)}",
        "periodo": {"mes": mes, "anio": anio},
        "total_empleados": len(filas),
        "saldos": sorted(filas, key=lambda x: x["empleado"]),
    }


def _consumos_batch(db, ids: list, eid: Optional[str], corte: date) -> dict:
    """Los consumos de TODOS los empleados en DOS queries, agrupados por empleado.

    Sin filtro de fechas a propósito: el saldo acumula períodos, así que acotar por mes —lo
    que hacía la versión vieja— dejaba afuera justo las licencias viejas que el vencimiento
    tiene que ver. El recorte lo hace el núcleo por PERÍODO, no la query por fecha.
    """
    out: dict[str, list] = {i: [] for i in ids}
    vac_q = (db.table("solicitudes_vacaciones")
             .select("empleado_id, dias, periodo, fecha_desde")
             .eq("cancelada", False).eq("tipo", "vacaciones").in_("empleado_id", ids))
    if eid:
        vac_q = vac_q.eq("empresa_id", eid)
    for v in (vac_q.execute().data or []):
        # `cancelada=false` ya está en el WHERE, así que lo único que separa "tomada" de
        # "planificada" es la fecha — la misma regla que services/_vacaciones_utils.derive_estado.
        # Que las dos den lo mismo lo verifica test_saldo_service_vs_r11.
        out.setdefault(v["empleado_id"], []).append(Consumo(
            dias=int(v.get("dias") or 0), periodo=v.get("periodo"),
            tomado=str(v.get("fecha_desde"))[:10] <= corte.isoformat()))

    pen_q = (db.table("vacaciones_pendientes")
             .select("empleado_id, periodo, dias_liquidados").in_("empleado_id", ids))
    if eid:
        pen_q = pen_q.eq("empresa_id", eid)
    for p in (pen_q.execute().data or []):
        if p.get("dias_liquidados"):  # sin liquidar no consume: los días siguen disponibles
            out.setdefault(p["empleado_id"], []).append(Consumo(
                dias=int(p["dias_liquidados"]), periodo=p.get("periodo"), tomado=True))
    return out


def _fila_saldo(emp: dict, consumos: list, corte: date) -> Dict[str, Any]:
    """Una fila del reporte. Todo el cálculo sale del núcleo compartido; acá no hay reglas.

    La rama "Sin asignar" de la versión anterior SE BORRÓ. Existía para
    `dias_vacaciones_asignados IS NULL`, que con la columna NOT NULL era código muerto; desde
    la migración 085 NULL es el caso NORMAL (19/19) y significa "regla general", no "falta el
    dato". Mantenerla habría puesto "Sin asignar" y saldo 0 en TODAS las filas.
    """
    ingreso = date.fromisoformat(str(emp["fecha_ingreso"])[:10]) if emp.get("fecha_ingreso") else None
    reconocida = emp.get("fecha_ingreso_reconocida")
    cupos = cupos_por_periodo(
        ingreso, date.fromisoformat(str(reconocida)[:10]) if reconocida else None,
        emp.get("dias_vacaciones_asignados"),
        periodos_a_calcular(ingreso, corte, consumos) if ingreso else [])
    s = saldo(cupos, consumos, corte)
    return {
        "empleado": _nombre(emp), "area": _area(emp),
        # Se mantiene el nombre "override" del campo crudo para que la columna no vuelva a
        # significar dos cosas: `asignados` es el cupo CALCULADO y vigente.
        "asignados": s.asignados, "gozados": s.gozados, "pedidos": s.pedidos,
        "disponibles": s.disponibles, "vencidos": s.vencidos,
    }
