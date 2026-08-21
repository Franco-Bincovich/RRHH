import { apiFetch } from "./api"

/**
 * 🔴 TODO ESTE ARCHIVO ES UN ESPEJO MANUAL de `backend/schemas/dashboard.py`, y el 21/8/2026 se
 * comprobó lo que eso cuesta: el backend borró `KPIResponse.costo_nomina` y el front lo siguió
 * declarando y pintando. **`tsc` no dice nada** —la interfaz es una afirmación del front sobre lo
 * que llega, no una lectura del contrato— así que la card mostró un valor vacío hasta que alguien
 * la miró. Es la tercera vez en el mes (antes: `candidatos.estado`, `fecha_egreso`/`motivo_baja`).
 *
 * Re-sincronizado campo por campo el 21/8/2026 contra `schemas/dashboard.py`. Al tocarlo:
 * compará las DOS listas enteras, no solo el campo que venías a agregar.
 */
export interface KPIDashboard {
  empleados_activos: number
  ingresos_mes: number
  bajas_mes: number
  onboardings_activos: number
  vacantes_activas: number
}

export interface AlertaDashboard {
  tipo: string
  mensaje: string
  nivel: "info" | "warning" | "error"
  /**
   * Ruta a la que lleva la alerta, ya armada por el backend (o null si no lleva a ninguna).
   * Reemplaza al `entidad_id` viejo, que acá se convertía SIEMPRE en `/empleados/{id}`: la
   * primera alerta de otro tipo con id habría linkeado a una ficha inexistente.
   * El front NO arma rutas de alertas: un mapa `tipo → ruta` de este lado sería un espejo
   * manual más, y las agregadas linkean a listados filtrados que no son un par (entidad, id).
   */
  href?: string | null
}

export interface HeadcountArea {
  area_id: string
  area: string
  total: number
}

/** Headcount de activos por EMPRESA (§6). `empresa_id` es `UUID` en el backend y viaja como
 *  string en el JSON. 🔑 La suma de esta lista ES `kpis.empleados_activos`: son el mismo universo
 *  partido en dos, y el backend tiene un test que lo fija (`test_dashboard_headcount.py`). */
export interface HeadcountEmpresa {
  empresa_id: string
  empresa: string
  total: number
}

export interface DistribItem {
  categoria: string
  total: number
}

export interface PersonaFecha {
  empleado: string
  fecha: string // dd/mm
}

export interface KpisExtra {
  ausencias_activas_hoy: number
  ausentismo_mes_pct: number
  ausentismo_nota: string
  masa_salarial_actual: number
  masa_salarial_anterior: number
  /**
   * 🔴 `null` = NO HAY BASE DE COMPARACIÓN, y NO es lo mismo que `0` (= la masa no se movió).
   * Hasta el 21/8/2026 el backend mandaba `0.0` en los dos casos y esta card afirmaba
   * "+0% vs mes anterior" sobre un dato que no existe. Con `costos_nomina` vacía —el estado de
   * producción hoy— ese es el valor que llega SIEMPRE. Quien lo formatee tiene que contemplar el
   * `null` explícitamente; el tipo está para que no se pueda olvidar.
   */
  masa_salarial_variacion_pct: number | null
  /** Preingresos que entran dentro de los próximos 30 días. NO es `kpis.ingresos_mes`, que cuenta
   *  por fecha a quien YA entró: son las dos puntas del mismo movimiento. */
  ingresos_proximos_30: number
  recategorizaciones_mes: number
  /** Bajas de los últimos 12 meses (por `fecha_egreso`) y su tasa sobre activos + bajas. */
  rotacion_12m_bajas: number
  rotacion_12m_pct: number
  /** §6 pide el promedio; la mediana viaja al lado porque el promedio ya miente con los datos
   *  reales (una de las dos empresas da 1,97 de promedio contra 1,22 de mediana). */
  antiguedad_promedio_anios: number
  antiguedad_mediana_anios: number
  distribucion_seniority: DistribItem[]
  distribucion_modalidad: DistribItem[]
  cumpleanos_mes: PersonaFecha[]
  aniversarios_mes: PersonaFecha[]
  /**
   * 🔴 NOMBRES DE LOS KPIs QUE NO SE PUDIERON CALCULAR. Existe en el backend desde la Sesión 5 y
   * el front NUNCA lo declaró: el fail-safe por KPI devuelve el vacío del campo (0 / lista vacía)
   * y lo anota acá, así que sin leer esto un KPI CAÍDO se pinta como un CERO MEDIDO. Es el mismo
   * bug que `+0% vs mes anterior`, y estaba a la vista desde que el campo nació.
   * Los nombres son los del backend (`_dashboard_kpis.calcular_extras`), no los títulos de card.
   */
  errores: string[]
}

export interface DashboardData {
  kpis: KPIDashboard
  headcount_por_area: HeadcountArea[]
  headcount_por_empresa: HeadcountEmpresa[]
  alertas: AlertaDashboard[]
  kpis_extra: KpisExtra
}

export function fetchDashboard(): Promise<DashboardData> {
  return apiFetch<DashboardData>("/api/dashboard")
}

// ── Panel "Requiere tu atención" (A6) ──────────────────────────────────────────

/**
 * Una alerta del panel de atención. Espejo de `AlertaAtencion`
 * (`backend/schemas/dashboard_atencion.py:22`).
 *
 * 🔴 `origen` ES EL DISCRIMINANTE Y NO ES COSMÉTICO: separa dos ciclos de vida distintos.
 *   · `"calculada"` — se DERIVA del padrón al leer (un ingreso que se viene, un período de
 *     prueba que termina). No tiene fila ni id: desaparece cuando desaparece su causa, y por eso
 *     NO se puede resolver a mano. El backend rechaza el intento con ALERTA_NO_RESOLUBLE (409).
 *   · `"manual"` — es una fila de `eventos_agenda` dentro de su ventana de aviso. Trae
 *     `evento_id` (con qué se resuelve) y `creado_por_nombre` (quién la creó).
 *
 * `tipo` es `string` y no una unión cerrada A PROPÓSITO, siguiendo al backend: un tipo calculado
 * nuevo no tiene por qué romper el front, que pinta por `origen`.
 */
export interface AlertaAtencion {
  origen: "calculada" | "manual"
  tipo: string
  mensaje: string
  /** Fecha del HECHO (el ingreso, el fin de prueba, el evento). Es la clave de orden. */
  fecha: string | null
  href: string | null
  evento_id: string | null
  creado_por_nombre: string | null
}

export interface AtencionData {
  alertas: AlertaAtencion[]
}

/** Las calculadas y las manuales en UNA lista, ya ordenada por fecha del hecho por el backend. */
export function fetchAtencion(): Promise<AtencionData> {
  return apiFetch<AtencionData>("/api/dashboard/atencion")
}

/**
 * Resuelve una alerta MANUAL. `origen` viaja en el body a propósito: es lo que le permite al
 * backend contestar ALERTA_NO_RESOLUBLE (409) cuando se intenta resolver una calculada, en vez
 * de un 404 mudo por un id que no existe.
 *
 * 🔴 El gate del backend es EVENTOS + WRITE, no DASHBOARD: resolver escribe un evento de agenda.
 * Un rol que puede VER el dashboard no necesariamente puede resolver — por eso el panel decide
 * si muestra el botón con el permiso de eventos, no con el de la pantalla.
 */
export function resolverAtencion(eventoId: string): Promise<unknown> {
  return apiFetch<unknown>("/api/dashboard/atencion/resolver", {
    method: "POST",
    body: JSON.stringify({ origen: "manual", evento_id: eventoId }),
  })
}
