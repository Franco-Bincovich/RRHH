import { apiFetch } from "./api"
import type {
  Asignacion, AsignacionBulkCreate, AsignacionBulkResult,
  AsignacionCreate, AsignacionListResponse, AsignacionUpdate,
  Hora, HoraCreate, HoraListResponse,
  Proyecto, ProyectoCreate, ProyectoListResponse, ProyectoUpdate,
} from "@/types/proyecto"

const BASE = "/api/proyectos"

// ── Proyectos ──────────────────────────────────────────────────────────────────

/**
 * Filtros del listado de proyectos. Un solo tipo, para que el día que este módulo tenga
 * export el filtro no pueda quedar en una sola de las dos puntas.
 */
export interface ProyectosFiltros {
  /** Override del header X-Empresa-Id (la empresa no viaja como query param). */
  empresaIdOverride?: string
  estado?: string
  /** Acota a proyectos con al menos un empleado asignado de esa área (semántica en el backend). */
  areaId?: string
}

/** Traducción filtros → query params. Fuente única. */
function queryProyectos(f: ProyectosFiltros): Record<string, string | undefined> {
  return { estado: f.estado, area_id: f.areaId }
}

export function fetchProyectos(filtros: ProyectosFiltros = {}): Promise<ProyectoListResponse> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(queryProyectos(filtros))) {
    if (v) params.set(k, v)
  }
  const qs = params.size ? `?${params}` : ""
  return apiFetch<ProyectoListResponse>(
    `${BASE}${qs}`,
    filtros.empresaIdOverride ? { headers: { "X-Empresa-Id": filtros.empresaIdOverride } } : {},
  )
}

export function fetchProyecto(id: string): Promise<Proyecto> {
  return apiFetch<Proyecto>(`${BASE}/${id}`)
}

export function createProyecto(body: ProyectoCreate): Promise<Proyecto> {
  return apiFetch<Proyecto>(BASE, { method: "POST", body: JSON.stringify(body) })
}

export function updateProyecto(id: string, body: ProyectoUpdate): Promise<Proyecto> {
  return apiFetch<Proyecto>(`${BASE}/${id}`, { method: "PUT", body: JSON.stringify(body) })
}

export function deleteProyecto(id: string): Promise<void> {
  return apiFetch<void>(`${BASE}/${id}`, { method: "DELETE" })
}

// ── Asignaciones ───────────────────────────────────────────────────────────────

export function fetchAsignaciones(proyectoId: string): Promise<AsignacionListResponse> {
  return apiFetch<AsignacionListResponse>(`${BASE}/${proyectoId}/asignaciones`)
}

export function createAsignacion(proyectoId: string, body: AsignacionCreate): Promise<Asignacion> {
  return apiFetch<Asignacion>(`${BASE}/${proyectoId}/asignaciones`, {
    method: "POST", body: JSON.stringify(body),
  })
}

/** Alta multi-selección: varios empleados en una sola llamada. Devuelve asignados + errores clasificados. */
export function asignarBulk(proyectoId: string, body: AsignacionBulkCreate): Promise<AsignacionBulkResult> {
  return apiFetch<AsignacionBulkResult>(`${BASE}/${proyectoId}/asignaciones/bulk`, {
    method: "POST", body: JSON.stringify(body),
  })
}

export function updateAsignacion(proyectoId: string, asigId: string, body: AsignacionUpdate): Promise<Asignacion> {
  return apiFetch<Asignacion>(`${BASE}/${proyectoId}/asignaciones/${asigId}`, {
    method: "PUT", body: JSON.stringify(body),
  })
}

export function deleteAsignacion(proyectoId: string, asigId: string): Promise<void> {
  return apiFetch<void>(`${BASE}/${proyectoId}/asignaciones/${asigId}`, { method: "DELETE" })
}

// ── Horas ──────────────────────────────────────────────────────────────────────

export function fetchHoras(proyectoId: string, page = 1, pageSize = 20): Promise<HoraListResponse> {
  return apiFetch<HoraListResponse>(`${BASE}/${proyectoId}/horas?page=${page}&page_size=${pageSize}`)
}

export function createHora(proyectoId: string, body: HoraCreate): Promise<Hora> {
  return apiFetch<Hora>(`${BASE}/${proyectoId}/horas`, {
    method: "POST", body: JSON.stringify(body),
  })
}

export function deleteHora(proyectoId: string, horaId: string): Promise<void> {
  return apiFetch<void>(`${BASE}/${proyectoId}/horas/${horaId}`, { method: "DELETE" })
}
