/**
 * ESPEJO de backend/utils/permisos.py. Fuente canónica = backend.
 * Mantener sincronizado. (Deuda: GET /api/auth/me eliminaría esta duplicación — Entrega 3.)
 *
 * Solo UX: filtra/oculta lo que el rol no puede usar. El control de seguridad real es
 * el backend (responde 403). Fail-closed: rol desconocido/null → sin acceso.
 */
import { getSession } from "@/services/api"
import type { UserRol } from "@/types/auth"

export type Accion = "read" | "write"

export type Seccion =
  | "empleados" | "areas" | "ausencias" | "vacaciones" | "vacantes"
  | "candidatos" | "onboarding" | "offboarding" | "costos" | "sucesion"
  | "assessment" | "organigrama" | "dashboard" | "empresa" | "reportes"
  | "importacion" | "integraciones" | "capacitaciones" | "evaluaciones"
  | "inventario" | "objetivos" | "usuarios" | "procesos" | "proyectos"
  | "auditoria" | "periodos" | "configuracion"

const MANDOS_MEDIOS_SECCIONES: ReadonlySet<Seccion> = new Set<Seccion>([
  "vacaciones",
  "ausencias",
])

/** Espejo de puede() del backend. 3 ramas + fail-closed ante rol desconocido/null. */
export function puede(rol: UserRol | null, seccion: Seccion, accion: Accion): boolean {
  if (rol === "admin_rrhh") return true
  if (rol === "gerencia_lectura") return accion === "read"
  if (rol === "mandos_medios") return MANDOS_MEDIOS_SECCIONES.has(seccion)
  return false
}

/** Rol del usuario logueado, o null si no hay sesión. */
export function getRol(): UserRol | null {
  return getSession()?.user.rol ?? null
}

/**
 * Mapa del primer segmento de la ruta → Seccion. Las rutas no listadas
 * (p. ej. /dashboard, /configuracion) devuelven null = siempre accesibles, no gateadas.
 *
 * ⚠️ /configuracion queda FUERA a propósito, aunque exista la sección "configuracion": esa
 * pantalla mezcla reglas de negocio (gateadas) con el cambio de contraseña y "Mi perfil", que
 * todo usuario necesita sea cual sea su rol. Gatear la RUTA entera dejaría a gerencia_lectura
 * y a mandos_medios sin poder cambiar su propia contraseña. El gate va POR BLOQUE, adentro.
 */
const RUTA_SECCION: Readonly<Record<string, Seccion>> = {
  empleados: "empleados",
  areas: "areas",
  ausencias: "ausencias",
  vacaciones: "vacaciones",
  equipo: "vacaciones",  // "Mi equipo": mismo gate que vacaciones (mandos_medios lo tiene)
  vacantes: "vacantes",
  candidatos: "candidatos",
  onboarding: "onboarding",
  offboarding: "offboarding",
  costos: "costos",
  sucesion: "sucesion",
  assessment: "assessment",
  organigrama: "organigrama",
  empresas: "empresa",
  reportes: "reportes",
  capacitaciones: "capacitaciones",
  evaluaciones: "evaluaciones",
  inventario: "inventario",
  objetivos: "objetivos",
  procesos: "procesos",
  proyectos: "proyectos",
  auditoria: "auditoria",
  periodos: "periodos",
  usuarios: "usuarios",
}

/** Seccion correspondiente a un pathname, o null si la ruta no se gatea por permiso. */
export function seccionDeRuta(pathname: string): Seccion | null {
  const seg = pathname.split("/").filter(Boolean)[0]
  if (!seg) return null
  return RUTA_SECCION[seg] ?? null
}

/**
 * Rutas gateables en el orden del sidebar, con su sección. Sirve para elegir el
 * destino de redirect cuando el rol no puede ver la ruta actual: se toma la primera
 * que sí puede leer (dashboard incluido, que admin y gerencia siempre leen).
 */
const RUTAS_ORDENADAS: ReadonlyArray<{ ruta: string; seccion: Seccion }> = [
  { ruta: "/dashboard", seccion: "dashboard" },
  { ruta: "/procesos", seccion: "procesos" },
  { ruta: "/proyectos", seccion: "proyectos" },
  { ruta: "/empresas", seccion: "empresa" },
  { ruta: "/empleados", seccion: "empleados" },
  { ruta: "/organigrama", seccion: "organigrama" },
  { ruta: "/vacantes", seccion: "vacantes" },
  { ruta: "/candidatos", seccion: "candidatos" },
  { ruta: "/vacaciones", seccion: "vacaciones" },
  { ruta: "/ausencias", seccion: "ausencias" },
  { ruta: "/onboarding", seccion: "onboarding" },
  { ruta: "/offboarding", seccion: "offboarding" },
  { ruta: "/costos", seccion: "costos" },
  { ruta: "/sucesion", seccion: "sucesion" },
  { ruta: "/capacitaciones", seccion: "capacitaciones" },
  { ruta: "/evaluaciones", seccion: "evaluaciones" },
  { ruta: "/inventario", seccion: "inventario" },
  { ruta: "/objetivos", seccion: "objetivos" },
  { ruta: "/reportes", seccion: "reportes" },
  { ruta: "/auditoria", seccion: "auditoria" },
  { ruta: "/periodos", seccion: "periodos" },
]

/** Primera ruta (en orden de nav) que el rol puede leer, o null si ninguna (fail-closed). */
export function primeraRutaPermitida(rol: UserRol | null): string | null {
  const item = RUTAS_ORDENADAS.find((r) => puede(rol, r.seccion, "read"))
  return item ? item.ruta : null
}
