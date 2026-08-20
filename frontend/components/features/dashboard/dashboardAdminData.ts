import { Briefcase, CalendarOff, DollarSign, TrendingUp, UserMinus, UserPlus, Users } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import {
  fetchAtencion, fetchDashboard,
  type AlertaAtencion, type AlertaDashboard, type DashboardData,
} from "@/services/dashboard"

/**
 * Los datos del dashboard de admin: la carga y los helpers de presentación (sin JSX).
 *
 * La carga vive acá y no en `DashboardAdmin` porque desde A6 son DOS endpoints con dos paneles
 * distintos, y quien decide qué pasa si uno de los dos falla es una regla de datos, no del
 * componente que los pinta. Ver `cargarDatosAdmin`.
 */
export interface KpiCardData {
  title: string
  value: string
  icon: LucideIcon
  description: string
}

export const NIVEL_VARIANT: Record<AlertaDashboard["nivel"], "default" | "secondary" | "destructive"> = {
  info:    "secondary",
  warning: "default",
  error:   "destructive",
}

export const NIVEL_LABEL: Record<AlertaDashboard["nivel"], string> = {
  info:    "Info",
  warning: "Aviso",
  error:   "Urgente",
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("es-AR", {
    style: "currency", currency: "ARS", maximumFractionDigits: 0,
  }).format(value)
}

function formatVariacion(pct: number): string {
  const signo = pct > 0 ? "+" : ""
  return `${signo}${pct}% vs mes anterior`
}

export function buildKpis(data: DashboardData): KpiCardData[] {
  const x = data.kpis_extra
  return [
    { title: "Colaboradores activos", value: String(data.kpis.empleados_activos), icon: Users, description: "Colaboradores vigentes" },
    { title: "Ingresos este mes", value: String(data.kpis.ingresos_mes), icon: UserPlus, description: "Nuevos ingresos del período" },
    { title: "Bajas este mes", value: String(data.kpis.bajas_mes), icon: UserMinus, description: "Egresos del período" },
    { title: "Costo total nómina", value: formatCurrency(data.kpis.costo_nomina), icon: DollarSign, description: "Mensual bruto" },
    { title: "Onboardings activos", value: String(data.kpis.onboardings_activos), icon: UserPlus, description: "Procesos en curso" },
    { title: "Vacantes activas", value: String(data.kpis.vacantes_activas), icon: Briefcase, description: "Posiciones abiertas" },
    { title: "Ausencias activas hoy", value: String(x.ausencias_activas_hoy), icon: CalendarOff, description: "Colaboradores ausentes hoy" },
    { title: "Ausentismo del mes", value: `${x.ausentismo_mes_pct}%`, icon: CalendarOff, description: x.ausentismo_nota },
    { title: "Masa salarial", value: formatCurrency(x.masa_salarial_actual), icon: TrendingUp, description: formatVariacion(x.masa_salarial_variacion_pct) },
  ]
}

/**
 * Los datos de los dos paneles de avisos, en una sola carga.
 *
 * 🔴 FAIL-SAFE POR ENDPOINT, igual que el `_safe` por KPI del backend: si `/atencion` falla, el
 * dashboard entero se muestra lo mismo y solo ese panel queda vacío y marcado. Al revés no: si
 * falla `/api/dashboard` no hay dashboard que mostrar, así que ese error se propaga.
 *
 * Las dos llamadas van EN PARALELO. Encadenarlas sumaría la latencia de la segunda a la primera
 * sin ninguna razón: no dependen entre sí, ni siquiera comparten filtro — las dos leen la
 * empresa activa del mismo header que `apiFetch` ya inyecta.
 */
export interface DatosAdmin {
  dashboard: DashboardData
  atencion: AlertaAtencion[]
  /** `true` = el panel de atención no pudo cargar. Distinto de "cargó y no hay nada". */
  atencionError: boolean
}

export async function cargarDatosAdmin(): Promise<DatosAdmin> {
  const [dashboard, atencion] = await Promise.all([
    fetchDashboard(),
    fetchAtencion().then((r) => r.alertas).catch(() => null),
  ])
  return { dashboard, atencion: atencion ?? [], atencionError: atencion === null }
}
