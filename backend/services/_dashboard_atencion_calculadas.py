"""
Las alertas CALCULADAS del panel "Requiere tu atención": ingresos próximos y fin de período de
prueba. Sin estado propio: se derivan del padrón AL LEER — no hay ningún job ni precálculo, y no
puede haberlo: Vercel mata el proceso al terminar el request y este repo no tiene tareas
programadas. Cada consulta evalúa las ventanas contra `hoy`.

Familia "dashboard" de `tests/test_acceso_a_datos.py`: las queries van directo a supabase,
igual que `_dashboard_alertas.py` — lecturas analíticas que ningún repo modela.

🔴 INGRESOS PRÓXIMOS **NO TIENE PISO DE FECHA**, igual que los eventos de agenda y por el motivo
escrito en `_eventos_pendientes`: un preingreso cuya fecha pasó y sigue en `preingreso` es el que
NADIE activó — el que más importa. Su causa se apaga cuando el pase a activo OCURRE
(`_empleado_activar`), no cuando el calendario pasa; ocultarlo al vencer sería perder justo el
aviso pendiente. La letra del pedido decía "dentro de los próximos 7 días"; el sin-piso extiende
hacia atrás, nunca recorta la ventana pedida.

🔴 FIN DE PRUEBA **SÍ TIENE PISO**, y la asimetría es el diseño, no un descuido: un período de
prueba cuyo fin ya pasó terminó SOLO — la causa desapareció con el calendario y no queda ninguna
acción pendiente que recordar. Alertar algo que el tiempo ya resolvió es ruido.
"""
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.dashboard_atencion import AlertaAtencion
from services.configuracion_service import ConfiguracionService

# El sistema de diseño avisa con una semana. Las dos calculadas comparten la ventana a
# propósito: dos números distintos serían dos definiciones de "próximo" en el mismo panel.
VENTANA_DIAS = 7

# 🔴 La ventana del KPI "Ingresos próximos 30 días" (`docs/SISTEMA-DE-DISENO.md` §6) es OTRA, y
# tiene que serlo: el PANEL avisa de lo que hay que hacer esta semana y el KPI mide el caudal del
# mes. Lo que NO puede ser otra es la definición de "ingreso próximo" —qué filas son— y por eso
# las dos ventanas cuelgan de la misma query (`_q_ingresos_proximos`) en vez de tener cada una la
# suya: dos queries que filtren "preingresos por fecha" pueden separarse en el próximo cambio de
# criterio, y ahí el panel y el KPI empiezan a contar gente distinta sin que nadie lo note.
VENTANA_KPI_DIAS = 30

# Espejo del CHECK `parametros_empresa_periodo_prueba_check` (periodo <= 730). Molde
# `_eventos_pendientes.TECHO_DIAS`: el recorte de la query es EXACTO, no una heurística — ningún
# empleado con `fecha_ingreso` anterior a hoy-730 puede tener el fin de prueba por delante ni
# con el período más largo que la base acepta. Si el CHECK sube, este número sube con él.
TECHO_PRUEBA_DIAS = 730


def _dmy(f: date) -> str:
    return f.strftime("%d/%m/%Y")


def _con_empresa(q, empresa_id: Optional[UUID]):
    """Barrera de empresa EN LA QUERY; None = consolidado, igual que en todo el dashboard."""
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


def _preingresos_hasta(q, empresa_id: Optional[UUID], hoy: date, dias: int):
    """EL PREDICADO de "ingreso próximo", en un solo lugar: `estado = 'preingreso'` y
    `fecha_ingreso` hasta hoy+`dias`. Sin piso de fecha (el porqué está en el encabezado).

    Lo usan el panel (7 días, con nombres) y el KPI del dashboard (30 días, solo el conteo). Lo
    único que cambia entre los dos es la ventana y la proyección.

    ⚠️ Recibe la query YA PROYECTADA en vez de armar el `select()` acá: cada uso necesita
    columnas distintas, y un `select()` construido con una variable deja de ser legible para
    `tests/test_selects_repos.py`, que valida las columnas contra `db/schema.sql` por AST.
    """
    return _con_empresa(
        q.eq("estado", "preingreso").lte("fecha_ingreso", str(hoy + timedelta(days=dias))),
        empresa_id)


def contar_ingresos_proximos(empresa_id: Optional[UUID], hoy: date,
                             dias: int = VENTANA_KPI_DIAS) -> int:
    """KPI "Ingresos próximos 30 días" (§6): cuántos preingresos entran dentro de la ventana.

    🔴 Cuenta `preingreso`, no "fecha_ingreso futura", y esa es la diferencia con "Ingresos este
    mes" (`dashboard_service`, que cuenta por FECHA a quien YA entró). Acá quien ya entró está en
    `activo` y queda afuera solo. Quien debía entrar y sigue en `preingreso` SÍ cuenta, igual que
    en el panel: no entró, así que su ingreso sigue pendiente.

    Va por `count="exact"` y no por `len(ingresos_proximos(...))`: el KPI es un número, y armar
    las alertas para tirarlas trae nombres y fechas de gente al pedo.
    """
    q = supabase_admin.table("empleados").select("id", count="exact")
    return _preingresos_hasta(q, empresa_id, hoy, dias).execute().count or 0


def ingresos_proximos(empresa_id: Optional[UUID], hoy: date) -> List[AlertaAtencion]:
    """Preingresos (A2/A4.2) con `fecha_ingreso` hasta hoy+7. Sin piso: ver el encabezado."""
    q = _preingresos_hasta(
        supabase_admin.table("empleados").select("id, nombre, apellido, fecha_ingreso"),
        empresa_id, hoy, VENTANA_DIAS)
    alertas = []
    for e in q.execute().data or []:
        fecha = date.fromisoformat(e["fecha_ingreso"])
        quien = f"{e['nombre']} {e['apellido']}"
        mensaje = (f"{quien} tiene ingreso previsto el {_dmy(fecha)}" if fecha >= hoy
                   else f"{quien} debía ingresar el {_dmy(fecha)} y sigue en preingreso")
        alertas.append(AlertaAtencion(origen="calculada", tipo="ingreso_proximo",
                                      mensaje=mensaje, fecha=fecha, href=f"/empleados/{e['id']}"))
    return alertas


def fin_de_prueba(empresa_id: Optional[UUID], hoy: date,
                  configuracion: ConfiguracionService) -> List[AlertaAtencion]:
    """Activos cuyo `fecha_ingreso + periodo_prueba_dias` cae entre hoy y hoy+7.

    El período es POR EMPRESA (`parametros_empresa.periodo_prueba_dias`, mig 114, default LCT
    90), así que el cálculo va en dos pasos: UNA query trae los candidatos posibles —el rango de
    `fecha_ingreso` que puede tener el fin por delante con CUALQUIER período que el CHECK
    admita— y el corte fino se hace en Python con el período de la empresa de cada uno. En
    consolidado son ≤5 lookups de parámetros (uno por empresa presente), nunca uno por fila.
    """
    q = _con_empresa(
        supabase_admin.table("empleados").select("id, nombre, apellido, fecha_ingreso, empresa_id")
        .eq("estado", "activo")
        .gte("fecha_ingreso", str(hoy - timedelta(days=TECHO_PRUEBA_DIAS)))
        # periodo >= 1 (CHECK): fin = ingreso + periodo <= hoy+7 exige ingreso <= hoy+6.
        .lte("fecha_ingreso", str(hoy + timedelta(days=VENTANA_DIAS - 1))),
        empresa_id)
    periodos: dict = {}
    alertas = []
    for e in q.execute().data or []:
        emp = str(e["empresa_id"])
        if emp not in periodos:
            periodos[emp] = configuracion.get_parametros(UUID(emp)).periodo_prueba_dias
        fin = date.fromisoformat(e["fecha_ingreso"]) + timedelta(days=periodos[emp])
        if hoy <= fin <= hoy + timedelta(days=VENTANA_DIAS):
            alertas.append(AlertaAtencion(
                origen="calculada", tipo="fin_periodo_prueba",
                mensaje=f"{e['nombre']} {e['apellido']} termina su período de prueba "
                        f"el {_dmy(fin)}",
                fecha=fin, href=f"/empleados/{e['id']}"))
    return alertas
