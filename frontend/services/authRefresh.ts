/**
 * Refresh de sesión y política de reintento ante 401.
 * Importa solo de session.ts: así api.ts puede importar de acá sin ciclo de módulos.
 */
import { marcarActividad } from "@/services/actividad"
import { API_BASE, clearSession, getSession, saveSession } from "@/services/session"

/** Refresh en vuelo. Mientras no sea null, los 401 concurrentes esperan ESTA promesa. */
let refreshEnVuelo: Promise<boolean> | null = null

/**
 * Pide un access_token nuevo con el refresh_token guardado y actualiza la sesión.
 * Usa fetch crudo a propósito (no apiFetch): así el refresh nunca reentra al
 * interceptor, que es lo único que haría posible un loop.
 */
export async function refreshSession(): Promise<boolean> {
  const session = getSession()
  if (!session?.refresh_token) return false
  try {
    const res = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    })
    if (!res.ok) return false
    const data = (await res.json()) as { access_token: string; refresh_token: string }
    saveSession({
      ...session,
      access_token: data.access_token,
      refresh_token: data.refresh_token,
    })
    return true
  } catch {
    return false
  }
}

/** Un solo refresh aunque N requests den 401 a la vez: las demás esperan la misma promesa. */
function refreshUnaVez(): Promise<boolean> {
  if (!refreshEnVuelo) {
    refreshEnVuelo = refreshSession().finally(() => {
      refreshEnVuelo = null
    })
  }
  return refreshEnVuelo
}

/** Limpia la sesión y manda a login. Hard nav: no hay router fuera de los componentes. */
function irALogin(): void {
  clearSession()
  if (typeof window !== "undefined") window.location.href = "/login"
}

/**
 * Ejecuta `construir` y, ante un 401, intenta UN refresh y reintenta UNA sola vez.
 * `construir` rearma la request entera (headers incluidos) para que el reintento tome
 * el access_token nuevo. No es recursiva: el reintento no vuelve a pasar por acá.
 */
export async function conRefresh(construir: () => Promise<Response>): Promise<Response> {
  const res = await construir()
  // Cualquier respuesta cuenta como actividad, incluso un 403: lo que importa es que el
  // backend VIO el request, que es exactamente cuándo sella `ultimo_acceso`. Va acá y no en
  // apiFetch para que también cuenten las subidas y las descargas, que no pasan por ahí.
  marcarActividad()
  if (res.status !== 401) return res

  const ok = await refreshUnaVez()
  if (!ok) {
    irALogin()
    return res
  }

  const reintento = await construir()
  if (reintento.status === 401) irALogin()
  return reintento
}
