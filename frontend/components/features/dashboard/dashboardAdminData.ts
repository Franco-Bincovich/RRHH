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

/**
 * Cuántos ítems se ven antes del corte en las listas del dashboard que crecen con la plantilla:
 * áreas, cumpleaños y aniversarios. Ninguna de las tres tiene techo (el backend devuelve una
 * fila por área y una por empleado que cumple en el mes), así que con 500 empleados las cards
 * empujan todo lo demás fuera de la pantalla.
 *
 * 6 y no 5 ni 10: una barra de headcount ocupa ~52px (nombre+número, la barra, y su gap), así
 * que 6 filas dejan la card de Headcount a la altura de la de Alertas que tiene al lado en la
 * grilla de 2 columnas — que es el alto que ya ocupa hoy sin empujar nada. Con las 12 áreas
 * cargadas el corte esconde la mitad, que es exactamente el punto.
 */
export const CORTE_LISTA = 6

/** Parte una lista en lo que se ve siempre y lo que queda detrás del desplegable. */
export function partirLista<T>(items: T[], corte: number = CORTE_LISTA): { visibles: T[]; resto: T[] } {
  return { visibles: items.slice(0, corte), resto: items.slice(corte) }
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
