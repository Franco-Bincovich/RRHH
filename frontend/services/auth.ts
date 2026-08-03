import { apiFetch, type Session } from "@/services/api"
import { clearSession } from "@/services/session"
import type { UserRol } from "@/types/auth"

export { refreshSession } from "@/services/authRefresh"

export interface UsuarioVigente {
  id: string
  /** null cuando el backend no pudo resolverlo (blip de base). NO es "sin rol". */
  rol: UserRol | null
}

/**
 * El estado del usuario SEGÚN EL BACKEND. El rol de `getSession()` es una foto del login: a
 * quien le cambian el rol le siguen apareciendo los botones de antes hasta que se vuelva a
 * loguear, y cada click termina en 403.
 *
 * Devuelve 403 si al usuario lo dieron de baja, así que también sirve de latido de sesión.
 */
export async function fetchUsuarioVigente(): Promise<UsuarioVigente> {
  return apiFetch<UsuarioVigente>("/api/auth/me")
}

/**
 * ¿Hay que adoptar el rol que devolvió el backend?
 *
 * `null` significa "no se pudo resolver", NUNCA "se quedó sin rol": adoptarlo dejaría al
 * usuario sin permisos en el front por un blip de base, mostrándole una app vacía en vez de
 * la suya. Ante la duda gana lo guardado, que el backend igual vuelve a chequear en cada
 * request — el front nunca es la barrera.
 */
export function rolDesactualizado(guardado: UserRol, vigente: UserRol | null): boolean {
  return vigente !== null && vigente !== guardado
}

export async function login(username: string, password: string): Promise<Session> {
  return apiFetch<Session>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  })
}

/**
 * Cierra la sesión: revoca el token en Supabase vía el backend y limpia la sesión local.
 * La llamada de red es best-effort — si falla, la sesión local se limpia igual, para no
 * dejar al usuario atrapado en una sesión que no puede cerrar.
 */
export async function logout(): Promise<void> {
  try {
    await apiFetch<void>("/api/auth/logout", { method: "POST" })
  } catch {
    // best-effort: el backend ya loguea el fallo de revocación
  } finally {
    clearSession()
  }
}
