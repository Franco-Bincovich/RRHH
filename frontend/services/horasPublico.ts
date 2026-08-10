import { API_BASE, ApiError } from "@/services/api"
import type {
  CargaHorasBody, CargaLicenciaBody, CargaLicenciaResultado, ClientePublico,
  Identificacion, Semana,
} from "@/types/horasPublico"

/**
 * El link PÚBLICO de carga de horas. Lo usa un empleado SIN cuenta en el sistema.
 *
 * 🔴 USA `fetch` DIRECTO Y NO `apiFetch`, y no es una preferencia de estilo.
 * `apiFetch` envuelve todo en `conRefresh`, el interceptor que ante un 401 intenta refrescar el
 * JWT y, si no puede, MANDA A `/login`. Acá el 401 no es un access token vencido: es el token de
 * SESIÓN del link. Pasar por ese camino haría que a un empleado sin cuenta se le vacíe la sesión
 * de otro usuario del navegador y termine en una pantalla de login que no le sirve para nada.
 * Además `apiFetch` agrega `Authorization` y `X-Empresa-Id`, dos headers que estas rutas no
 * miran y que no tienen por qué viajar. Es el mismo motivo por el que `services/assessment.ts`
 * hace fetch directo en sus dos rutas públicas.
 *
 * El manejo de errores sí se comparte: se levanta el MISMO `ApiError` que el resto de la app,
 * con el `code` y el `message` que mandó el backend. Los mensajes del backend son en castellano
 * y accionables ("Ese día ya tenés 10 horas cargadas y el máximo es 12"); reemplazarlos por un
 * genérico tiraría justo lo que el usuario necesita para resolverlo.
 */
const BASE = `${API_BASE}/api/horas-publico`

async function pedir<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { message?: string; code?: string }
    throw new ApiError(body.message ?? "Error del servidor", body.code ?? "UNKNOWN", res.status)
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}

export function identificar(dni: string): Promise<Identificacion> {
  return pedir<Identificacion>(`${BASE}/identificar`, {
    method: "POST", body: JSON.stringify({ dni }),
  })
}

export function fetchClientes(token: string): Promise<{ items: ClientePublico[] }> {
  return pedir<{ items: ClientePublico[] }>(
    `${BASE}/clientes?token=${encodeURIComponent(token)}`)
}

export function fetchSemana(token: string): Promise<Semana> {
  return pedir<Semana>(`${BASE}/semana?token=${encodeURIComponent(token)}`)
}

export function cargarHoras(body: CargaHorasBody): Promise<unknown> {
  return pedir(`${BASE}/horas`, { method: "POST", body: JSON.stringify(body) })
}

export function cargarLicencia(body: CargaLicenciaBody): Promise<CargaLicenciaResultado> {
  return pedir<CargaLicenciaResultado>(`${BASE}/licencia`, {
    method: "POST", body: JSON.stringify(body),
  })
}
