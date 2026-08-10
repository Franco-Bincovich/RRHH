import { getEmpresaActivaId } from "@/services/empresaStore"
import { conRefresh } from "@/services/authRefresh"
import { API_BASE, getSession } from "@/services/session"

// Re-exports: los consumidores siguen importando la sesión desde "@/services/api".
export type { Session } from "@/services/session"
export { API_BASE, clearSession, getSession, saveSession } from "@/services/session"

// Rutas de auth que NO pasan por el interceptor: un 401 acá es credencial inválida o
// refresh_token muerto, no un access_token vencido. Sin esta exclusión, un login con
// contraseña incorrecta dispararía un refresh y un redirect a /login en vez de mostrar
// el error al usuario.
const RUTAS_SIN_REFRESH = ["/api/auth/login", "/api/auth/refresh"]

/**
 * 🔴 EL MÁXIMO `page_size` QUE ACEPTA EL BACKEND. Pedir más NO devuelve menos filas: FastAPI
 * rechaza el request con **422** antes de tocar un service, así que la pantalla se queda sin
 * NINGÚN dato.
 *
 * Los seis routers paginados lo declaran igual —`Query(20, ge=1, le=100)` en `empleados`,
 * `vacaciones`, `vacaciones_pendientes`, `ausencias`, `auditoria` y `proyecto_horas`—, o sea que
 * es una propiedad del backend y no de un endpoint. Vive acá, en la capa HTTP compartida, para
 * que haya UNA fuente y no un `100` repetido en cada modal.
 *
 * ⚠️ SUBIR ESTE NÚMERO SOLO NO ALCANZA: el tope real está en el `le=100` de los routers, y este
 * const es el espejo. Cambiarlo de un lado deja el otro rechazando o truncando en silencio.
 *
 * Ya rompió dos pantallas: `useDestinatarios` (envío de plantillas) y `useCandidatosProyecto`
 * (asignar empleados a un proyecto) pedían 200 y mostraban "no hay datos" con la base llena,
 * porque el `.catch` de cada hook convertía el 422 en una lista vacía. Hay un barrido que
 * verifica que ningún call site del listado de empleados vuelva a pasarse:
 * `services/pageSize.test.ts`.
 */
export const MAX_PAGE_SIZE = 100

// ── Request helpers ────────────────────────────────────────────────────────────

export function authHeaders(): Record<string, string> {
  const session = getSession()
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`
  }
  const empresaId = getEmpresaActivaId()
  headers["X-Empresa-Id"] = empresaId ?? "todas"
  return headers
}

// ── Error type ─────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(message: string, code: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.code = code
    this.status = status
  }
}

/**
 * Traduce una respuesta HTTP de error al `ApiError` que ve el resto del front.
 *
 * 🔴 EXPORTADA PARA PODER TESTEARLA CONTRA EL CONTRATO DEL BACKEND, no porque alguien de afuera
 * la llame. Es el embudo ÚNICO de `apiFetch`, `postMultipart` y `descargarArchivo`: lo que esta
 * función no encuentra en el body, el usuario no lo ve nunca. `services/api.test.ts` la alimenta
 * con `Response` reales cuyo cuerpo es IDÉNTICO al que assertea
 * `backend/tests/test_validacion_422.py`, así que si un lado mueve el contrato, el otro rojea.
 *
 * ⚠️ El test NO puede reimplementarla ni envolverla. Reimplementada, un `message` que el backend
 * renombre a `mensaje` seguiría "pasando" en el front, que es exactamente el modo de falla que
 * este test existe para cubrir: la copia del test acierta y el código de producción no.
 */
export async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as { message?: string; code?: string }
    return new ApiError(body.message ?? "Error del servidor", body.code ?? "UNKNOWN", res.status)
  } catch {
    return new ApiError("Error del servidor", "UNKNOWN", res.status)
  }
}

// ── Fetch wrapper ──────────────────────────────────────────────────────────────

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const construir = () =>
    fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { ...authHeaders(), ...(init.headers as Record<string, string> | undefined) },
    })
  const res = RUTAS_SIN_REFRESH.includes(path) ? await construir() : await conRefresh(construir)
  if (!res.ok) throw await toApiError(res)
  if (res.status === 204) return undefined as T // logout responde 204 sin body
  return res.json() as Promise<T>
}

// ── Subida de archivos (multipart genérico) ─────────────────────────────────────

/**
 * Sube un archivo a `path` vía multipart/form-data. Agrega `file` + cada par de `campos`
 * como campos de texto del form. Omite Content-Type a propósito: así el browser fija el
 * boundary del multipart automáticamente (no funciona si se envía application/json).
 */
export async function subirArchivo<T>(
  path: string,
  file: File,
  campos?: Record<string, string>,
): Promise<T> {
  const form = new FormData()
  form.append("file", file)
  if (campos) for (const [k, v] of Object.entries(campos)) form.append(k, v)
  return postMultipart<T>(path, form)
}

/**
 * POST multipart/form-data genérico a partir de un FormData ya armado (archivo opcional +
 * campos). Omite Content-Type a propósito: el browser fija el boundary automáticamente.
 */
export async function postMultipart<T>(path: string, form: FormData): Promise<T> {
  const construir = () => {
    const headers = authHeaders()
    delete headers["Content-Type"] // el browser fija el boundary multipart
    return fetch(`${API_BASE}${path}`, { method: "POST", headers, body: form })
  }
  const res = await conRefresh(construir)
  if (!res.ok) throw await toApiError(res)
  return res.json() as Promise<T>
}

// ── Descarga de archivos (motor de export genérico) ─────────────────────────────

export type FormatoExport = "pdf" | "excel" | "csv" | "word"

const EXPORT_EXT: Record<string, string> = { pdf: "pdf", excel: "xlsx", csv: "csv", word: "docx" }

/** Descarga el blob de `path?formato=...` y dispara la descarga con la extensión correcta. */
export async function descargarArchivo(
  path: string,
  formato: string,
  nombreBase: string,
  extraHeaders?: Record<string, string>,
  params?: Record<string, string | undefined>,
): Promise<void> {
  const query = new URLSearchParams({ formato })
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v) query.set(k, v)
  }
  const construir = () =>
    fetch(`${API_BASE}${path}?${query}`, {
      headers: { ...authHeaders(), ...extraHeaders },
    })
  const res = await conRefresh(construir)
  if (!res.ok) throw await toApiError(res)
  const blob = await res.blob()
  const ext = EXPORT_EXT[formato] ?? formato
  const safe = nombreBase.replace(/[^\w\s-]/g, "").trim() || "export"
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `${safe}.${ext}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
