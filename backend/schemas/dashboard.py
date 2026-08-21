"""
Schemas de respuesta para el módulo de Dashboard Ejecutivo.
"""
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class KPIResponse(BaseModel):
    """Los KPIs "principales", que son counts sobre el mes en curso.

    🔴 `costo_nomina` SE FUE el 21/8/2026, y no se renombró: se BORRÓ. Era la suma de
    `costos_nomina.salario_bruto` y convivía en la misma pantalla con `masa_salarial_actual`, que
    suma `costos_nomina.total`. Dos cards, dos fórmulas, la misma tabla. El porqué de cuál
    sobrevive está entero en `services/_dashboard_masa_salarial.py`.
    ⚠️ `ingresos_mes`, `bajas_mes` y `onboardings_activos` NO están entre los diez KPIs de §6.
    Se conservan porque son datos correctos que la pantalla ya usa y cuestan un count cada uno;
    cuáles de todos entran en la grilla de diez lo decide la sesión de front, no el payload.
    """

    empleados_activos: int
    ingresos_mes: int
    bajas_mes: int
    onboardings_activos: int
    vacantes_activas: int


class AlertaResponse(BaseModel):
    tipo: str
    mensaje: str
    nivel: Literal["info", "warning", "error"]
    # Ruta del front a la que lleva la alerta, o None si no lleva a ninguna parte.
    #
    # 🔴 Reemplaza al `entidad_id` anterior, que el front convertía SIEMPRE en
    # `/empleados/{id}`: la primera alerta de otro tipo con id habría linkeado a una ficha de
    # empleado inexistente. El molde de adjuntos (entidad + entidad_id) tampoco alcanzaba —
    # una alerta agregada lleva a un LISTADO FILTRADO (`/empleados?sin_manager=true`), que no
    # es un par (entidad, id).
    #
    # La ruta la arma el backend a propósito: quien sabe a dónde lleva una alerta es quien la
    # genera. Un mapa `tipo → ruta` en el front sería otro espejo manual que puede divergir,
    # como `permisos.ts` vs `permisos.py`.
    href: Optional[str] = None


class HeadcountAreaResponse(BaseModel):
    area_id: str
    area: str
    total: int


class HeadcountEmpresaResponse(BaseModel):
    """Headcount de activos de una empresa (§6). Hermano de `HeadcountAreaResponse`.

    `empresa_id` va tipado `UUID` y no `str` como el `area_id` de al lado: es la regla #1 del
    porteo a asyncpg y rige para lo que se escribe DESDE HOY. El de arriba es de antes y está
    declarado en `tests/test_ids_tipados.py`; alinearlo es otra tarea.
    """

    empresa_id: UUID
    empresa: str
    total: int


class DistribItem(BaseModel):
    categoria: str
    total: int


class PersonaFecha(BaseModel):
    empleado: str
    fecha: str  # dd/mm del cumpleaños o aniversario


class KPIsExtraResponse(BaseModel):
    """KPIs calculados con fail-safe INDIVIDUAL (`_dashboard_kpis.calcular_extras`): si uno falla,
    queda en su vacío y los demás salen igual. Empty state: 0 / listas vacías, nunca un error.

    Nació en la Sesión 5 con cinco (23/26/27/28/30) y desde el 21/8/2026 lleva además los que
    faltaban de `docs/SISTEMA-DE-DISENO.md` §6.
    """

    ausencias_activas_hoy: int
    ausentismo_mes_pct: float
    ausentismo_nota: str
    masa_salarial_actual: float
    masa_salarial_anterior: float
    # 🔴 `None` = NO HAY BASE DE COMPARACIÓN. No es lo mismo que `0.0` (= la masa no se movió), y
    # hasta el 21/8/2026 era lo mismo: el cálculo caía en `0.0` cuando el mes anterior no tenía
    # nada cargado y el front lo pintaba con signo, o sea que la pantalla AFIRMABA "+0% vs mes
    # anterior" sobre un dato inexistente — que es lo que dice hoy, con `costos_nomina` vacía.
    # El razonamiento completo, y por qué un mes cargado en 0 también da `None`, están en
    # `services/_dashboard_masa_salarial.py`. Molde: `DashboardCostosResponse.variacion_porcentual`.
    masa_salarial_variacion_pct: Optional[float] = None
    # ── Los que faltaban de §6 ────────────────────────────────────────────────────────────────
    # Preingresos que entran dentro de los próximos 30 días. NO es `ingresos_mes` (ése cuenta por
    # fecha a quien YA entró): son las dos puntas del mismo movimiento, y §6 pide ésta.
    ingresos_proximos_30: int = 0
    recategorizaciones_mes: int = 0
    # Bajas de los últimos 12 meses y su tasa. Por `empleados.fecha_egreso`, que NO es la fuente
    # del reporte R6 — la divergencia está declarada en `services/_dashboard_operacion.py`.
    rotacion_12m_bajas: int = 0
    rotacion_12m_pct: float = 0.0
    # §6 pide "antigüedad promedio"; la mediana viaja al lado porque acá el promedio ya miente
    # (una empresa da 1,97 de promedio contra 1,22 de mediana). Ver `_dashboard_antiguedad.py`.
    antiguedad_promedio_anios: float = 0.0
    antiguedad_mediana_anios: float = 0.0
    distribucion_seniority: List[DistribItem]
    distribucion_modalidad: List[DistribItem]
    cumpleanos_mes: List[PersonaFecha]
    aniversarios_mes: List[PersonaFecha]
    errores: List[str] = []  # KPIs que fallaron (fail-safe por KPI): quedaron en vacío/0


class DashboardResponse(BaseModel):
    kpis: KPIResponse
    headcount_por_area: List[HeadcountAreaResponse]
    # Su propia sección con su propio `_safe`, igual que la de áreas: son dos cortes del mismo
    # universo y ninguno tiene por qué caerse si el otro falla.
    headcount_por_empresa: List[HeadcountEmpresaResponse] = []
    alertas: List[AlertaResponse]
    kpis_extra: KPIsExtraResponse
