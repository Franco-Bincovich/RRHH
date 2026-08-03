import { Briefcase, CalendarOff, DollarSign, TrendingUp, UserMinus, UserPlus, Users } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import type { AlertaDashboard, DashboardData } from "@/services/dashboard"

/** Constantes, tipos y helpers puros del dashboard de admin (sin JSX). */
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
    { title: "Empleados activos", value: String(data.kpis.empleados_activos), icon: Users, description: "Colaboradores vigentes" },
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
