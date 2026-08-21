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
  | "auditoria" | "periodos" | "configuracion" | "clientes"
  | "perfiles_puesto" | "recategorizaciones" | "eventos"

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
 *
 * ⚠️ /comunicacion SÍ entra, con esa MISMA sección, y no es una contradicción: ahí no vive nada
 * que todo usuario necesite —son las plantillas de mail, el envío y su historial—, así que
 * gatear la ruta entera es correcto. Es el mismo permiso que el backend ya exige en esos tres
 * endpoints. No se creó una `Seccion` nueva porque `puede()` es genérica: una sección propia
 * daría el mismo resultado a cambio de tocar el espejo manual con `permisos.py`.
 */
const RUTA_SECCION: Readonly<Record<string, Seccion>> = {
  empleados: "empleados",
  // Los que todavía no entraron son legajos: mismo gate que /empleados. La pantalla lista
  // `estado=preingreso` y su única escritura es `POST /api/empleados/{id}/activar`, que el
  // backend gatea con Seccion.EMPLEADOS + WRITE.
  "proximos-ingresos": "empleados",
  // Los que se fueron gatean con OFFBOARDING y no con EMPLEADOS: el dato de la baja pertenece
  // al proceso de egreso, es el mismo permiso con el que el ítem entra al sidebar, y así quien
  // puede ver el padrón no ve automáticamente quién se fue ni por qué.
  bajas: "offboarding",
  areas: "areas",
  ausencias: "ausencias",
  vacaciones: "vacaciones",
  equipo: "vacaciones",  // "Mi equipo": mismo gate que vacaciones (mandos_medios lo tiene)
  vacantes: "vacantes",
  candidatos: "candidatos",
  // El catálogo de plantillas de búsqueda. 🔴 Es el ÚNICO listado que NO se acota por
  // empresa —ninguna ruta del backend lee `X-Empresa-Id`, el catálogo es del grupo—, pero
  // eso no lo exime del GATE: sin esta entrada `seccionDeRuta` devuelve null y el AuthGuard
  // lee ese null como "pasá". Global no es lo mismo que público.
  "perfiles-puesto": "perfiles_puesto",
  // La planilla de cambios de rol/seniority/categoría. El HISTORIAL de la ficha gatea con
  // esta misma sección aunque se muestre bajo /empleados: el permiso lo decide de QUÉ es
  // el dato, no en qué pantalla se ve. Es el criterio que el backend ya aplica en
  // `recategorizaciones_empleado.py`.
  recategorizaciones: "recategorizaciones",
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
  clientes: "clientes",
  eventos: "eventos",
  // La vista interna de horas gatea con PROYECTOS: el dato son filas de horas_proyecto, cuyo
  // gate publicado ya es ese. Ver el encabezado de routers/horas_cliente.py.
  "horas-por-cliente": "proyectos",
  // Plantillas de mail + envío + historial. Ruta propia desde el 7/8/2026; el permiso sigue
  // siendo el de configuración, que es el que gatea esos endpoints en el backend.
  comunicacion: "configuracion",
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
  { ruta: "/proximos-ingresos", seccion: "empleados" },
  { ruta: "/organigrama", seccion: "organigrama" },
  { ruta: "/vacantes", seccion: "vacantes" },
  { ruta: "/candidatos", seccion: "candidatos" },
  { ruta: "/perfiles-puesto", seccion: "perfiles_puesto" },
  { ruta: "/vacaciones", seccion: "vacaciones" },
  { ruta: "/ausencias", seccion: "ausencias" },
  { ruta: "/recategorizaciones", seccion: "recategorizaciones" },
  { ruta: "/onboarding", seccion: "onboarding" },
  { ruta: "/offboarding", seccion: "offboarding" },
  { ruta: "/bajas", seccion: "offboarding" },
  { ruta: "/costos", seccion: "costos" },
  { ruta: "/sucesion", seccion: "sucesion" },
  { ruta: "/capacitaciones", seccion: "capacitaciones" },
  { ruta: "/evaluaciones", seccion: "evaluaciones" },
  { ruta: "/inventario", seccion: "inventario" },
  { ruta: "/objetivos", seccion: "objetivos" },
  { ruta: "/reportes", seccion: "reportes" },
  { ruta: "/auditoria", seccion: "auditoria" },
  { ruta: "/periodos", seccion: "periodos" },
  { ruta: "/clientes", seccion: "clientes" },
  { ruta: "/eventos", seccion: "eventos" },
  { ruta: "/horas-por-cliente", seccion: "proyectos" },
]

/** Primera ruta (en orden de nav) que el rol puede leer, o null si ninguna (fail-closed). */
export function primeraRutaPermitida(rol: UserRol | null): string | null {
  const item = RUTAS_ORDENADAS.find((r) => puede(rol, r.seccion, "read"))
  return item ? item.ruta : null
}
