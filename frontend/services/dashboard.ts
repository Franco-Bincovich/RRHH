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
