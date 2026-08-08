import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"
import type { EmpleadoListResponse } from "@/types/empleado"

/** Usuario del sistema, para selectores (espeja GET /api/usuarios del backend). */
export interface UsuarioOption {
  id: string
  nombre: string
  apellido: string
  email: string
  username: string
  rol: string
}

export interface UsuarioListResponse {
  items: UsuarioOption[]
  total: number
}

/** Payload de alta de un usuario. `rol` viaja pero el backend lo revalida (ROLES_VALIDOS). */
export interface CrearUsuarioPayload {
  nombre: string
  apellido: string
  email: string
  username: string
  rol: string
  empleado_id?: string // opcional: vincula el user a su registro de empleado
}

/** Respuesta del alta: la contraseña temporal se muestra UNA sola vez. */
export interface CrearUsuarioResult {
  id: string
  username: string
  password_temporal: string
}

/** Empleado en el shape liviano del selector de vinculación (líderes o todos). */
export interface EmpleadoLider {
  id: string
  nombre: string
  apellido: string
  legajo: string | null
}

/** Lista los usuarios activos del sistema (para el selector de operador en filtros). */
export async function fetchUsuarios(): Promise<UsuarioListResponse> {
  return apiFetch<UsuarioListResponse>("/api/usuarios")
}

/**
 * Exporta el listado de usuarios — las MISMAS filas que muestra la pantalla.
 *
 * `fetchUsuarios` no manda ningún query param, y este tampoco: no hay filtros que puedan
 * quedar en una sola de las dos puntas. 🔴 El día que el listado gane un filtro, NO se lo
 * agregue solo acá ni solo allá: los dos tienen que armar sus params con UNA función de
 * traducción compartida (molde: `queryProyectos` en services/proyectos.ts). Si el filtro
 * queda solo en el listado, el archivo sale con más filas de las que se ven, sin aviso.
 *
 * Tampoco viaja `X-Empresa-Id`: los usuarios no cuelgan de una empresa (decisión de producto),
 * así que el selector del sidebar no aplica a esta pantalla.
 */
export function exportarUsuarios(formato: FormatoExport): Promise<void> {
  return descargarArchivo("/api/usuarios/exportar", formato, "usuarios")
}

/** Crea un usuario mandos_medios; devuelve la contraseña temporal (no recuperable). */
export async function crearUsuario(payload: CrearUsuarioPayload): Promise<CrearUsuarioResult> {
  return apiFetch<CrearUsuarioResult>("/api/usuarios", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

/** Elimina un usuario del sistema por id (el backend bloquea la auto-eliminación). */
export async function eliminarUsuario(id: string): Promise<void> {
  await apiFetch<void>(`/api/usuarios/${id}`, { method: "DELETE" })
}

/** Cambia la contraseña del usuario autenticado (self-service). */
export async function cambiarPassword(passwordActual: string, passwordNueva: string): Promise<void> {
  await apiFetch<{ ok: boolean }>("/api/usuarios/cambiar-password", {
    method: "POST",
    body: JSON.stringify({ password_actual: passwordActual, password_nueva: passwordNueva }),
  })
}

/** Trae empleados activos del selector (shape liviano). `query` define el filtro extra. */
async function fetchEmpleadosSelector(query: string): Promise<EmpleadoLider[]> {
  const res = await apiFetch<EmpleadoListResponse>(`/api/empleados?${query}`)
  return res.items.map((e) => ({ id: e.id, nombre: e.nombre, apellido: e.apellido, legajo: e.legajo }))
}

/** Empleados LÍDERES activos (es_lider=true) — para vincular a un mando medio. */
export async function fetchEmpleadosLideres(): Promise<EmpleadoLider[]> {
  return fetchEmpleadosSelector("es_lider=true&estado=activo&page_size=100")
}

/** TODOS los empleados activos (omite es_lider) — para vincular a admin/gerencia. */
export async function fetchEmpleadosTodos(): Promise<EmpleadoLider[]> {
  return fetchEmpleadosSelector("estado=activo&page_size=100")
}
