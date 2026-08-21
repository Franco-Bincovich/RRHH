import type { ElementType } from "react"
import {
  Activity, FolderKanban, LayoutDashboard, Users, UsersRound, GitBranch, Briefcase,
  UserPlus, UserMinus, UserX, Umbrella, CalendarX2, DollarSign, TrendingUp,
  BarChart3, GraduationCap, ClipboardCheck, Target, ScrollText,
  CalendarClock, Settings, Settings2, Building2, UserCog, UserSearch, Network, Mail, Handshake,
  Clock, Timer, CalendarHeart, CalendarPlus, FolderOpen, IdCard, Route, ArrowUpNarrowWide,
  Search, LogIn, LogOut, Sparkles, ClipboardList,
} from "lucide-react"

import type { Accion, Seccion } from "@/services/permisos"
import type { UserRol } from "@/types/auth"

// seccion: null = ítem siempre visible; resto = se filtra por puede(rol, seccion, accion).
// accion: permiso requerido para ver el ítem (default "read"); "write" = solo quien escribe.
// soloRol: si está definido, el ítem se muestra solo si el rol está en la lista (Y ADEMÁS
//   pasa el gating de sección). undefined = sin restricción por rol (comportamiento de siempre).
// href: AUSENTE en los ítems `proximamente`. Un ítem de menú que apunta a una ruta que no existe
//   en app/ es un 404, y el barrido de nav-config.test.ts lo rojea.
// proximamente: la pantalla todavía no existe. El ítem se VE (comunica que la sección está
//   contemplada) pero no navega y sale del recorrido con teclado. Mismo mecanismo que el
//   `<Tab disabled>` de empresas/[id]/page.tsx, que es donde el repo ya lo resolvió una vez.
export interface NavLink {
  label: string
  href?: string
  icon: ElementType
  seccion: Seccion | null
  accion?: Accion
  soloRol?: UserRol[]
  proximamente?: boolean
}

export interface NavGroupDef {
  label: string
  icon: ElementType
  items: NavLink[]
}

// ─── Fuera de los grupos, arriba (sistema de diseño §4) ───────────────────────
// Dashboard · Reportes · Auditoría no cuelgan de ningún grupo: son las tres vistas
// transversales que se consultan desde cualquier módulo, no un módulo más.
export const ITEMS_SUPERIORES: ReadonlyArray<NavLink> = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, seccion: null },
  { label: "Reportes", href: "/reportes", icon: BarChart3, seccion: "reportes" },
  { label: "Auditoría", href: "/auditoria", icon: ScrollText, seccion: "auditoria" },
]

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

// INVENTARIO está FUERA DEL MENÚ por el sistema de diseño §4 ("hasta nuevo aviso").
// NO se borró nada más: /inventario sigue siendo una ruta viva y alcanzable por URL, con su
// `Seccion.inventario` en permisos.ts y su gate en el AuthGuard. Volver a mostrarlo es agregar
// una línea acá; sacar la ruta o la sección no sería reversible del mismo modo.

// ─── Los 6 grupos (sistema de diseño §4) ─────────────────────────────────────
// Assessment sigue oculto (módulo no habilitado por ASSESSMENT_ENABLED).
export const NAV_GROUPS: ReadonlyArray<NavGroupDef> = [
  { label: "Personas", icon: Users, items: [
    { label: "Colaboradores", href: "/empleados", icon: Users, seccion: "empleados" },
    { label: "Organigrama", href: "/organigrama", icon: GitBranch, seccion: "organigrama" },
    // "Mi equipo" (roster de ownership): seccion "vacaciones" para pasar el gating de sección,
    // + soloRol ["mandos_medios"] para que NO lo vean admin/gerencia (redundante con Colaboradores).
    { label: "Mi equipo", href: "/equipo", icon: UsersRound, seccion: "vacaciones", soloRol: ["mandos_medios"] },
    // Sin pantalla: el backend de adjuntos es polimórfico y vive colgado de cada ficha, pero no
    // hay una vista de documentación por persona ni un service de front que la sirva.
    { label: "Documentación / Legajos", icon: FolderOpen, seccion: "empleados", proximamente: true },
  ] },
  { label: "Reclutamiento", icon: Search, items: [
    { label: "Vacantes", href: "/vacantes", icon: Briefcase, seccion: "vacantes" },
    { label: "Candidatos", href: "/candidatos", icon: UserSearch, seccion: "candidatos" },
    // El catálogo de plantillas de búsqueda (mig 113/116). Tarjetas, no lista: sistema de
    // diseño §5. 🔴 Es del GRUPO — el selector de empresa del sidebar no lo filtra, y la
    // pantalla lo dice en el encabezado porque es lo contrario a lo que hace el resto.
    { label: "Perfiles de puesto", href: "/perfiles-puesto", icon: IdCard, seccion: "perfiles_puesto" },
  ] },
  { label: "Incorporación", icon: LogIn, items: [
    { label: "Onboarding", href: "/onboarding", icon: UserPlus, seccion: "onboarding" },
    // Los legajos en `preingreso`, ordenados por fecha de ingreso: quién entra primero. El
    // botón "Confirmar ingreso" de cada fila es POST /empleados/{id}/activar (bloque A2/A3).
    { label: "Próximos Ingresos", href: "/proximos-ingresos", icon: CalendarPlus, seccion: "empleados" },
  ] },
  { label: "Talento y Desarrollo", icon: Sparkles, items: [
    { label: "Objetivos", href: "/objetivos", icon: Target, seccion: "objetivos" },
    { label: "Evaluaciones", href: "/evaluaciones", icon: ClipboardCheck, seccion: "evaluaciones" },
    { label: "Formación", href: "/capacitaciones", icon: GraduationCap, seccion: "capacitaciones" },
    // Sin pantalla NI backend: es el único ítem del documento que no tiene nada detrás en
    // ninguna capa. El propio sistema de diseño lo marca "(Próximamente)".
    { label: "Plan de desarrollo", icon: Route, seccion: "capacitaciones", proximamente: true },
    ...(SUCESION_ACTIVA ? [SUCESION_ITEM] : []),
  ] },
  { label: "Gestión", icon: ClipboardList, items: [
    { label: "Ausencias / Licencias", href: "/ausencias", icon: CalendarX2, seccion: "ausencias" },
    { label: "Vacaciones", href: "/vacaciones", icon: Umbrella, seccion: "vacaciones" },
    // La planilla de cambios de rol, seniority o categoría (mig 113/117), más su historial en la
    // ficha del colaborador. 🔴 OJO CON LO QUE PROMETE, y la pantalla ya lo respeta: NO hay flujo
    // de aprobación ni impacto porcentual (§7). Es registro puro —se carga y queda registrado— y
    // el impacto es un MONTO en pesos, que además se oculta sin permiso de costos.
    { label: "Recategorizaciones", href: "/recategorizaciones", icon: ArrowUpNarrowWide, seccion: "recategorizaciones" },
    // Vivía dentro de /configuracion. Se sacó a ruta propia el 7/8/2026: desde ahí ahora se
    // MANDAN mails, y eso es operación recurrente, no configuración. La `seccion` sigue siendo
    // "configuracion" a propósito — es el permiso que el backend ya exige; ver la página.
    { label: "Comunicación", href: "/comunicacion", icon: Mail, seccion: "configuracion" },
    { label: "Procesos", href: "/procesos", icon: Activity, seccion: "procesos" },
    // Agenda de eventos (migración 113): se carga un evento, se lo ve venir en el dashboard y se
    // lo resuelve. Es operación semanal, no un catálogo de Administración.
    { label: "Eventos", href: "/eventos", icon: CalendarHeart, seccion: "eventos" },
  ] },
  { label: "Egresos", icon: LogOut, items: [
    { label: "Offboarding", href: "/offboarding", icon: UserMinus, seccion: "offboarding" },
    // Los legajos en `baja`, del más reciente al más viejo, con motivo y antigüedad al egreso.
    // Es de SOLO LECTURA: dar de baja se hace efectivizando un offboarding (el ítem de arriba)
    // o importando la nómina con `Fecha Baja`.
    { label: "Bajas", href: "/bajas", icon: UserX, seccion: "offboarding" },
  ] },
]

// ─── Administración: al final, separada de los 6 ─────────────────────────────
export const ADMIN_GROUP: NavGroupDef = {
  label: "Administración", icon: Settings2, items: [
    { label: "Empresas", href: "/empresas", icon: Building2, seccion: "empresa" },
    { label: "Áreas", href: "/areas", icon: Network, seccion: "areas" },
    { label: "Usuarios", href: "/usuarios", icon: UserCog, seccion: "usuarios", accion: "write" },
    { label: "Períodos", href: "/periodos", icon: CalendarClock, seccion: "periodos" },
    { label: "Configuración", href: "/configuracion", icon: Settings, seccion: null },
    { label: "Costos", href: "/costos", icon: DollarSign, seccion: "costos" },
    { label: "Proyectos", href: "/proyectos", icon: FolderKanban, seccion: "proyectos" },
    // Catálogo GLOBAL de clientes (migración 102/109): master data que carga Capital Humano y
    // que es el eje de "Horas por cliente".
    { label: "Clientes", href: "/clientes", icon: Handshake, seccion: "clientes" },
    // Gatea con "proyectos", igual que el backend: el dato son filas de horas_proyecto.
    { label: "Horas por cliente", href: "/horas-por-cliente", icon: Clock, seccion: "proyectos" },
    // Sin pantalla INTERNA: /horas existe pero es el link PÚBLICO, fuera de (dashboard), sin
    // AuthGuard y apagado por HORAS_PUBLICO_ENABLED=false. Enlazarlo desde acá daría una
    // pantalla sin sesión y hoy además desmontada. El sistema de diseño lo marca "(Próximamente)".
    { label: "Carga de horas", icon: Timer, seccion: "proyectos", proximamente: true },
  ],
}

// Los 7 grupos en orden de render. Es lo que barren los tests: si Administración no entrara acá,
// sus ítems quedarían fuera del espejo con permisos.ts y del barrido de rutas.
export const TODOS_LOS_GRUPOS: ReadonlyArray<NavGroupDef> = [...NAV_GROUPS, ADMIN_GROUP]
