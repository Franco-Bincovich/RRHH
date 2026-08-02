"""
Alertas del Dashboard Ejecutivo — cómo se consultan y en qué orden salen. El catálogo de QUÉ
se alerta (tablas, textos, destinos) vive en _dashboard_alertas_catalogo.py.

Extraído de dashboard_service.py, que no tenía margen para esto contra su límite de 150. La
costura sigue siendo `DashboardService._generar_alertas`: el método se conserva como delegador
de una línea porque es lo que `_safe` envuelve (fail-safe por sección) y lo que los tests
parchean por instancia. Mover la implementación no mueve el punto de corte.

🚨 NO agregar try/except acá adentro: `_safe` ya envuelve la generación entera. Un except
propio se tragaría un fallo que hoy queda anotado en `errores` y en el log de la sección.

⚠️ Toda alerta filtra por empresa EN LA QUERY (`.eq("empresa_id", ...)`), nunca en Python sobre
un fetch sin filtrar: el dashboard es VISTA y respeta el selector del sidebar, así que una
alerta que cuente filas de otra empresa fuga datos en cuanto exista la segunda. Las cinco
tablas de bloqueo tienen `empresa_id` propio (verificado contra el catálogo), así que las cinco
usan la Forma A y ninguna necesita resolver la empresa por un join.

Tres familias, en orden de valor:
  1. BLOQUEOS DE MÓDULO — una tabla vacía deja un módulo entero inutilizable. Son las de mejor
     relación valor/esfuerzo: un conteo por tabla y un mensaje que dice qué hacer.
  2. CAMPOS VACÍOS del padrón — agregadas con conteo y link al listado filtrado.
  3. DERIVADAS DE KPIs — informativas, sin acción asociada.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.dashboard import AlertaResponse, KPIResponse
from services._dashboard_alertas_catalogo import BLOQUEOS, CAMPOS_VACIOS, Bloqueo, CampoVacio

# Orden de render: lo accionable primero. Antes salían en orden de generación, así que las
# informativas quedaban arriba y lo que había que hacer, abajo del pliegue.
_PESO_NIVEL = {"error": 0, "warning": 1, "info": 2}

# Por debajo de este conteo la alerta de campo vacío sale NOMINAL (una por empleado, con link a
# su ficha: llegás y lo cargás). Por encima colapsa a una sola línea con el total — con 19
# empleados sin superior, 19 líneas idénticas no son 19 veces más útiles: son un panel que
# nadie vuelve a mirar.
_UMBRAL_NOMINAL = 5


def _con_empresa(q, empresa_id: Optional[UUID]):
    """Filtro de empresa EN LA QUERY. None = consolidado (no restringe), igual que en el resto."""
    return q.eq("empresa_id", str(empresa_id)) if empresa_id else q


def generar_alertas(kpis: KPIResponse, empresa_id: Optional[UUID] = None) -> List[AlertaResponse]:
    """Alertas del dashboard, ordenadas por nivel (lo accionable arriba)."""
    alertas: List[AlertaResponse] = []
    for bloqueo in BLOQUEOS:
        alertas.extend(_alerta_de_bloqueo(bloqueo, empresa_id))
    for campo in CAMPOS_VACIOS:
        alertas.extend(_alertas_de_campo_vacio(campo, empresa_id))
    alertas.extend(_alertas_de_kpis(kpis))
    # `sorted` es estable: dentro de cada nivel se conserva el orden del catálogo.
    return sorted(alertas, key=lambda a: _PESO_NIVEL[a.nivel])


def _alerta_de_bloqueo(b: Bloqueo, empresa_id: Optional[UUID]) -> List[AlertaResponse]:
    """Una alerta si la tabla no tiene ninguna fila para esta empresa; ninguna si tiene.
    Se pregunta por la EXISTENCIA (limit 1), no por el total: el conteo exacto no cambiaría el
    mensaje y en una tabla grande cuesta más."""
    q = _con_empresa(supabase_admin.table(b.tabla).select("id").limit(1), empresa_id)
    if q.execute().data:
        return []
    return [AlertaResponse(tipo=b.tipo, nivel=b.nivel, mensaje=b.mensaje, href=b.href)]


def _alertas_de_campo_vacio(c: CampoVacio, empresa_id: Optional[UUID]) -> List[AlertaResponse]:
    """Nominal por debajo del umbral (link a cada ficha), agregada por encima (link al listado
    filtrado). Se auto-resuelve al cargar el dato: la query es en vivo, no hay estado que
    limpiar ni alerta que cerrar a mano."""
    # `estado = activo`, NO `!= baja`: tiene que ser el MISMO predicado que lleva el
    # href_listado, o el número del mensaje no coincide con lo que ve quien hace clic.
    q = _con_empresa(
        supabase_admin.table("empleados").select("id, nombre, apellido", count="exact")
        .is_(c.campo, "null").eq("estado", "activo"),
        empresa_id,
    )
    res = q.execute()
    filas = res.data or []
    total = res.count if res.count is not None else len(filas)
    if total == 0:
        return []
    if total <= _UMBRAL_NOMINAL:
        return [
            AlertaResponse(tipo=c.tipo, nivel=c.nivel, href=f"/empleados/{e['id']}",
                           mensaje=f"{e['nombre']} {e['apellido']} no tiene {c.falta}")
            for e in filas
        ]
    return [AlertaResponse(
        tipo=c.tipo, nivel=c.nivel, href=c.href_listado,
        mensaje=f"{total} empleados sin {c.falta} — {c.consecuencia}",
    )]


def _alertas_de_kpis(kpis: KPIResponse) -> List[AlertaResponse]:
    """Informativas derivadas de los KPIs ya calculados: no consultan la base de nuevo."""
    alertas: List[AlertaResponse] = []
    if kpis.vacantes_activas > 0:
        alertas.append(AlertaResponse(tipo="vacantes", nivel="info", href="/vacantes",
            mensaje=f"Hay {kpis.vacantes_activas} vacante(s) activa(s) en proceso de selección"))
    if kpis.onboardings_activos > 0:
        alertas.append(AlertaResponse(tipo="onboarding", nivel="info", href="/onboarding",
            mensaje=f"Hay {kpis.onboardings_activos} proceso(s) de onboarding en curso"))
    return alertas
