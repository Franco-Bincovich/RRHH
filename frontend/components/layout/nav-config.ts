import type { ElementType } from "react"
import {
  Activity, FolderKanban, LayoutDashboard, Users, UsersRound, GitBranch, Briefcase,
  UserPlus, UserMinus, Umbrella, CalendarX2, DollarSign, TrendingUp,
  BarChart3, GraduationCap, ClipboardCheck, Package, Target, ScrollText,
  CalendarClock, Settings, Building2, UserCog, UserSearch,
} from "lucide-react"

import type { Accion, Seccion } from "@/services/permisos"
import type { UserRol } from "@/types/auth"

// seccion: null = ítem siempre visible; resto = se filtra por puede(rol, seccion, accion).
// accion: permiso requerido para ver el ítem (default "read"); "write" = solo quien escribe.
// soloRol: si está definido, el ítem se muestra solo si el rol está en la lista (Y ADEMÁS
//   pasa el gating de sección). undefined = sin restricción por rol (comportamiento de siempre).
export interface NavLink {
  label: string
  href: string
  icon: ElementType
  seccion: Seccion | null
  accion?: Accion
  soloRol?: UserRol[]
}

export interface NavGroupDef {
  label: string
  items: NavLink[]
}

// Dashboard: item fijo arriba, fuera del acordeón.
export const DASHBOARD_ITEM: NavLink = {
  label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, seccion: null,
}

// ─── Módulos ocultos ──────────────────────────────────────────────────────────
// Sucesión está OCULTA por decisión de producto, no borrada: la página, sus 11 archivos de
// components/features/sucesion/, services/sucesion.ts y todo el backend (endpoints, permisos,
// tests) siguen enteros.
//
// PARA REACTIVARLA (dos líneas, una por archivo):
//   1. acá:                                  SUCESION_ACTIVA = true
//   2. app/(dashboard)/sucesion/page.tsx:    useState(true) en el gate `moduloActivo`
// Sin el paso 2 el ítem vuelve al sidebar pero la página redirige igual a /dashboard.
//
// El tipo es `boolean` explícito y NO el literal inferido: con `= false` a secas TS colapsa la
// constante a `false`, la rama true del ternario queda inalcanzable y volver a `true` deja de
// type-checkear solo. Mismo motivo por el que el gate de la página es useState y no const.
const SUCESION_ACTIVA: boolean = false

const SUCESION_ITEM: NavLink = {
  label: "Sucesión", href: "/sucesion", icon: TrendingUp, seccion: "sucesion",
}

// Grupos colapsables, en orden de aparición. Assessment sigue oculto (módulo no habilitado).
export const NAV_GROUPS: ReadonlyArray<NavGroupDef> = [
  { label: "Personas", items: [
    { label: "Empleados", href: "/empleados", icon: Users, seccion: "empleados" },
    { label: "Organigrama", href: "/organigrama", icon: GitBranch, seccion: "organigrama" },
    // "Mi equipo" (roster de ownership): seccion "vacaciones" para pasar el gating de sección,
    // + soloRol ["mandos_medios"] para que NO lo vean admin/gerencia (redundante con Empleados).
    { label: "Mi equipo", href: "/equipo", icon: UsersRound, seccion: "vacaciones", soloRol: ["mandos_medios"] },
    { label: "Vacaciones", href: "/vacaciones", icon: Umbrella, seccion: "vacaciones" },
    { label: "Ausencias", href: "/ausencias", icon: CalendarX2, seccion: "ausencias" },
  ] },
  { label: "Incorporación", items: [
    { label: "Vacantes", href: "/vacantes", icon: Briefcase, seccion: "vacantes" },
    { label: "Candidatos", href: "/candidatos", icon: UserSearch, seccion: "candidatos" },
    { label: "Onboarding", href: "/onboarding", icon: UserPlus, seccion: "onboarding" },
    { label: "Offboarding", href: "/offboarding", icon: UserMinus, seccion: "offboarding" },
    ...(SUCESION_ACTIVA ? [SUCESION_ITEM] : []),
  ] },
  { label: "Operación", items: [
    { label: "Procesos", href: "/procesos", icon: Activity, seccion: "procesos" },
    { label: "Proyectos", href: "/proyectos", icon: FolderKanban, seccion: "proyectos" },
    { label: "Inventario", href: "/inventario", icon: Package, seccion: "inventario" },
  ] },
  { label: "Desempeño", items: [
    { label: "Capacitaciones", href: "/capacitaciones", icon: GraduationCap, seccion: "capacitaciones" },
    { label: "Evaluaciones", href: "/evaluaciones", icon: ClipboardCheck, seccion: "evaluaciones" },
    { label: "Objetivos", href: "/objetivos", icon: Target, seccion: "objetivos" },
  ] },
  { label: "Análisis", items: [
    { label: "Costos", href: "/costos", icon: DollarSign, seccion: "costos" },
    { label: "Reportes", href: "/reportes", icon: BarChart3, seccion: "reportes" },
    { label: "Auditoría", href: "/auditoria", icon: ScrollText, seccion: "auditoria" },
  ] },
  { label: "Administración", items: [
    { label: "Empresas", href: "/empresas", icon: Building2, seccion: "empresa" },
    { label: "Usuarios", href: "/usuarios", icon: UserCog, seccion: "usuarios", accion: "write" },
    { label: "Períodos", href: "/periodos", icon: CalendarClock, seccion: "periodos" },
    { label: "Configuración", href: "/configuracion", icon: Settings, seccion: null },
  ] },
]
