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
  entidad_id?: string | null // id del registro (ej. empleado) para linkear a su ficha
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
