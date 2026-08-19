import { apiFetch } from "./api"

export interface KPIDashboard {
  empleados_activos: number
  ingresos_mes: number
  bajas_mes: number
  costo_nomina: number
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
  masa_salarial_variacion_pct: number
  distribucion_seniority: DistribItem[]
  distribucion_modalidad: DistribItem[]
  cumpleanos_mes: PersonaFecha[]
  aniversarios_mes: PersonaFecha[]
}

export interface DashboardData {
  kpis: KPIDashboard
  headcount_por_area: HeadcountArea[]
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
