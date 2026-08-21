"""
Los dos KPIs del bloque "Operación" de `docs/SISTEMA-DE-DISENO.md` §6 que no tenían dueño:
**recategorizaciones del mes** y **rotación de los últimos 12 meses**.

Los otros cuatro del bloque ya lo tenían y no se duplican acá: colaboradores activos y búsquedas
abiertas están en `dashboard_service._calcular_kpis`, ausencias en curso en `_dashboard_kpis`, e
ingresos próximos sale de `_dashboard_atencion_calculadas.contar_ingresos_proximos` — el mismo
predicado que alimenta el panel "Requiere tu atención", con otra ventana.

Familia "dashboard" de `tests/test_acceso_a_datos.py` para la rotación (un count analítico que
ningún repo modela). Las recategorizaciones **sí** van por su repo: existe, ya pagina y ya filtra
por rango, así que abrir una query propia sería una segunda definición de "recategorización del
mes" al lado de la que la planilla usa.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 LA ROTACIÓN SE CUENTA POR `empleados.fecha_egreso`, NO POR `offboarding_instancias`
═══════════════════════════════════════════════════════════════════════════════════════════
Son dos números distintos y hay que elegir uno:

  · `offboarding_instancias` cuenta las bajas que pasaron por el TRÁMITE de offboarding. Es lo
    que usa el reporte R6 (`reportes/_reporte_dotacion.generate_rotacion`).
  · `empleados.fecha_egreso` cuenta TODAS las bajas, hayan pasado por el trámite o no.

Manda `fecha_egreso`, porque **la baja tiene dos vías y solo una crea instancia**: el import de
nómina con columna `Fecha Baja` llama a `dar_de_baja(...)` derecho, sin instancia de offboarding
(ver `utils/estados_empleado.py`, "LA BAJA TIENE DOS VÍAS Y SOLO DOS"). Contar por instancias
deja afuera a todo el que se fue por esa vía, que es la vía masiva. Además `fecha_egreso` es
CUÁNDO SE FUE la persona, y `offboarding_instancias.created_at` es cuándo se cargó el trámite:
para un corte de 12 meses la diferencia entre las dos fechas cae justo en los bordes.

⚠️ **CONSECUENCIA DECLARADA, NO RESUELTA: el reporte R6 y este KPI cuentan distinto.** Con
`offboarding_instancias` en 0 filas hoy los dos dan 0 y nadie lo nota — que es exactamente cómo
se veía la masa salarial duplicada antes de esta misma tanda. Está anotado en
`docs/DEUDA-TECNICA.md`: unificar R6 sobre `fecha_egreso` es una decisión de producto (el reporte
desagrega por `motivo_egreso`, que vive en la instancia; el legajo tiene su propio `motivo_baja`),
y se toma aparte, no de rebote acá.
"""
import calendar
from datetime import date, timedelta
from typing import Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories.recategorizacion_repo import RecategorizacionRepo

# 🔴 365 días corridos hacia atrás, no `hoy.replace(year=hoy.year - 1)`: el 29/2 no existe en el
# año anterior y esa forma levanta ValueError un día de cada 1461. El corrimiento de ~6 h por
# año bisiesto no mueve un conteo mensual de bajas.
DIAS_12_MESES = 365


def _rango_mes(anio: int, mes: int) -> Tuple[date, date]:
    return date(anio, mes, 1), date(anio, mes, calendar.monthrange(anio, mes)[1])


def recategorizaciones_mes(anio: int, mes: int, empresa_id: Optional[UUID]) -> int:
    """KPI "Recategorizaciones del mes" (§6): cuántas RIGIERON en el mes en curso.

    El rango va sobre `fecha_efectiva` —cuándo rigió— y no sobre `created_at` —cuándo se cargó—,
    porque lo decide el repo y no este KPI. Con fecha retroactiva las dos difieren, y la pregunta
    de RRHH ("qué cambió este mes") es siempre la primera.

    Pide `page_size=1` y descarta los items: lo que se usa es el `total` del filtro sin paginar,
    que es la única cifra autoritativa (la regla del wrapper paginado, ver `schemas/objetivo.py`).
    """
    desde, hasta = _rango_mes(anio, mes)
    _, total = RecategorizacionRepo().find_all(
        page=1, page_size=1, empresa_id=empresa_id, fecha_desde=desde, fecha_hasta=hasta)
    return total


def rotacion_12m(hoy: date, empresa_id: Optional[UUID]) -> Tuple[int, float]:
    """KPI "Rotación 12 meses" (§6): (bajas de los últimos 12 meses, tasa %).

    La tasa es `bajas / (activos + bajas) * 100`, la MISMA forma que ya usa el reporte R6: lo
    que este KPI cambia es de dónde salen las bajas y qué ventana mira, no cómo se divide.

    · `.eq("estado", "baja")` además del rango: una `fecha_egreso` cargada no alcanza para ser
      una baja. Es el mismo filtro que `_reporte_movimientos` tuvo que agregar cuando se
      descubrió que faltaba (el caso vivo: un preingreso que se cae antes de entrar y al que le
      cargan la fecha aparecería como rotación que nunca ocurrió).
    · Techo en `hoy`: la rotación del último año son las bajas que YA ocurrieron. Una
      `fecha_egreso` futura es una baja programada, no una consumada.
    """
    eid = str(empresa_id) if empresa_id else None
    bajas_q = (supabase_admin.table("empleados").select("id", count="exact")
               .eq("estado", "baja")
               .gte("fecha_egreso", str(hoy - timedelta(days=DIAS_12_MESES)))
               .lte("fecha_egreso", str(hoy)))
    activos_q = supabase_admin.table("empleados").select("id", count="exact").eq("estado", "activo")
    if eid:
        bajas_q = bajas_q.eq("empresa_id", eid)
        activos_q = activos_q.eq("empresa_id", eid)
    bajas = bajas_q.execute().count or 0
    base = (activos_q.execute().count or 0) + bajas
    return bajas, (round(bajas / base * 100, 2) if base else 0.0)
