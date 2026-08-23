/**
 * Refresh de sesión y política de reintento ante 401.
 * Importa solo de session.ts: así api.ts puede importar de acá sin ciclo de módulos.
 */
import { marcarActividad } from "@/services/actividad"
import { API_BASE, clearSession, getSession, saveSession } from "@/services/session"

/**
 * 🔴 LOS ÚNICOS `code` DE 401 QUE SIGNIFICAN "TU SESIÓN DEJÓ DE VALER", y por eso los únicos que
 * deslogean. Leídos del backend uno por uno:
 *
 *   · MISSING_TOKEN         middleware/auth.py:109 — no vino el header Authorization.
 *                           routers/auth.py:25 — el logout, que lo exige a mano.
 *   · INVALID_TOKEN         middleware/auth.py:117 — firma, `exp` o `kid` rechazados por el JWKS.
 *   · SESION_EXPIRADA       middleware/auth.py:144 — 8 h sin un solo request.
 *   · INVALID_REFRESH_TOKEN services/auth_service.py:99 — el refresh mismo fue rechazado.
 *
 * 🔴 EL 401 NO ES UN ESTADO DE SESIÓN. Significa "esta request no está autorizada", y el backend
 * lo usa para cosas que no tienen nada que ver con la sesión de este navegador. Los que existen
 * hoy, y qué pasaba cuando el interceptor miraba solo el status:
 *
 *   · GMAIL_TOKEN_EXPIRED — la casilla del SISTEMA perdió el acceso a Google. Es una integración
 *     caída, no una sesión vencida. **Es el bug que este archivo cierra**: /vacantes pide los
 *     mails pendientes al montar (`MailsPendientes.tsx`), recibía este 401 y mandaba al login a
 *     un usuario perfectamente autenticado, en cada carga de la pantalla.
 *     Desde el mismo arreglo el backend lo emite **502** (`services/_google_token.py`), así que
 *     ya no llegaría acá. La entrada se queda igual: el front no puede apoyarse en que ningún
 *     backend futuro vuelva a mandar un 401 ajeno — el status por sí solo nunca fue suficiente.
 *   · INVALID_CREDENTIALS — `services/usuario_service.py:82`: "la contraseña ACTUAL que
 *     escribiste está mal", en /cambiar-password. Esa ruta SÍ pasa por acá (no está en
 *     `RUTAS_SIN_REFRESH`, que solo excluye login y refresh), así que hasta este arreglo
 *     **equivocarte de contraseña al cambiarla te deslogueaba**. Segundo bug de la misma familia,
 *     encontrado buscando el primero.
 *   · SESION_INVALIDA / IDENTIFICACION_INVALIDA — el link público de horas. Hoy no llegan acá
 *     (`services/horasPublico.ts` hace fetch directo, a propósito y documentado), pero son el
 *     precedente del que sale este patrón: `esSesionMuerta` en
 *     `components/features/horasPublico/logica.ts` ya decidía por `code` y tiene test.
 *
 * 🛡️ ESTA LISTA NO SE MANTIENE A MANO. `backend/tests/test_espejo_codes_401.py` barre TODOS los
 * 401 del backend y exige que cada uno esté acá o declarado ahí con su razón. Un 401 de auth
 * nuevo que nadie agregue rojea; uno ajeno que alguien agregue de más, también.
 */
const CODES_SESION_MUERTA: ReadonlySet<string> = new Set([
  "MISSING_TOKEN",
  "INVALID_TOKEN",
  "SESION_EXPIRADA",
  "INVALID_REFRESH_TOKEN",
])

/** Refresh en vuelo. Mientras no sea null, los 401 concurrentes esperan ESTA promesa. */
let refreshEnVuelo: Promise<boolean> | null = null

/**
 * ¿Este 401 dice que la sesión de este navegador dejó de valer?
 *
 * 🔴 SE DECIDE POR EL `code` DEL BODY, NUNCA POR EL STATUS. Ver `CODES_SESION_MUERTA`.
 *
 * 🔴 `res.clone()` NO ES UN DETALLE. El body de una `Response` se lee UNA sola vez: leerlo acá
 * dejaría el stream consumido, y `toApiError` (`services/api.ts:76`) —que corre después sobre la
 * MISMA `Response`— caería en su `catch` y devolvería "Error del servidor" con code `UNKNOWN`.
 * O sea: sin el clone, arreglar el logout rompería el mensaje de TODOS los errores de la app.
 * Hay un test que lo cubre leyendo el body después de pasar por acá.
 *
 * 🔴 UN 401 SIN `code`, CON BODY ILEGIBLE O CON UN CODE DESCONOCIDO **NO DESLOGUEA**, y la
 * asimetría es a propósito: no desloguear a alguien que debía salir es una molestia de un
 * request (el siguiente vuelve a dar 401 y el usuario ve el error), mientras que desloguear por
 * un 401 ajeno destruye la sesión y el trabajo a medio cargar — que es exactamente este bug.
 * Y en la práctica el caso "sin code" es un 401 que NO produjo nuestro backend (un proxy, la
 * protección de deployment de Vercel): tratarlo como sesión vencida es adivinar.
 * ⚠️ Lo que se pierde: ese caso no queda registrado del lado del cliente. Los que sí produce el
 * backend ya se loguean allá con code y path (`middleware/error_handler.py:30-33`), que es un
 * lugar más útil que la consola del navegador; y este repo no tiene logger de front ni un solo
 * `console.*` en código de producción, así que no se agrega el primero por esto.
 */
async function esSesionMuerta(res: Response): Promise<boolean> {
  try {
    const body = (await res.clone().json()) as { code?: unknown }
    return typeof body.code === "string" && CODES_SESION_MUERTA.has(body.code)
  } catch {
    return false
  }
}

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
 * Ejecuta `construir` y, ante un 401 DE NUESTRA SESIÓN, intenta UN refresh y reintenta UNA sola
 * vez. `construir` rearma la request entera (headers incluidos) para que el reintento tome el
 * access_token nuevo. No es recursiva: el reintento no vuelve a pasar por acá.
 *
 * Cualquier otra respuesta —incluido un 401 ajeno y cualquier 403— se devuelve TAL CUAL, y el
 * caller la ve como el `ApiError` que armó el backend, con su `code` y su mensaje.
 */
export async function conRefresh(construir: () => Promise<Response>): Promise<Response> {
  const res = await construir()
  // Cualquier respuesta cuenta como actividad, incluso un 403: lo que importa es que el
  // backend VIO el request, que es exactamente cuándo sella `ultimo_acceso`. Va acá y no en
  // apiFetch para que también cuenten las subidas y las descargas, que no pasan por ahí.
  marcarActividad()
  // El `status !== 401` corta antes de clonar y parsear: en el camino feliz esto no cuesta nada.
  if (res.status !== 401 || !(await esSesionMuerta(res))) return res

  const ok = await refreshUnaVez()
  if (!ok) {
    irALogin()
    return res
  }

  const reintento = await construir()
  // El reintento se juzga con el MISMO criterio: si vuelve 401 pero por un motivo ajeno (el
  // token nuevo es válido y lo que falla es una integración), tampoco desloguea.
  if (reintento.status === 401 && (await esSesionMuerta(reintento))) irALogin()
  return reintento
}
