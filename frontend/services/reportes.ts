import { apiFetch, API_BASE, authHeaders } from "./api"

export type TipoReporte = "headcount" | "rotacion" | "altas_bajas" | "distribucion" | "costos" | "vacantes" | "onboarding" | "adhoc" | "anual_consolidado" | "saldos_vacaciones" | "ausentismo" | "listado_vac_aus" | "presupuesto" | "capacitacion" | "auditoria"

export type VistaAusentismo = "total" | "injustificado" | "ambos"

export interface ReporteGenerarRequest {
  tipo: TipoReporte
  mes?: number
  anio?: number
  prompt?: string
  // Armado manual: empresa y área salen del FORM, NO del selector del sidebar.
  empresa_id?: string // omitido = consolidado (todas las empresas)
  area_id?: string // omitido = todas las áreas de la empresa
  vista?: VistaAusentismo // solo ausentismo
}

export interface ReporteResponse {
  id: string
  nombre: string
  tipo: string
  datos: Record<string, unknown>
  generado_por: string
  created_at: string
}

export interface HistorialItem {
  id: string
  nombre: string
  tipo: string
  generado_por: string
  created_at: string
  empresa_id: string | null
  empresa_nombre: string | null
}

export function generarReporte(body: ReporteGenerarRequest): Promise<ReporteResponse> {
  return apiFetch<ReporteResponse>("/api/reportes/generar", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function fetchHistorial(): Promise<HistorialItem[]> {
  return apiFetch<HistorialItem[]>("/api/reportes/historial")
}

export async function exportarReporte(
  id: string,
  formato: "pdf" | "excel",
  nombre: string,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/reportes/${id}/exportar?formato=${formato}`,
    { headers: authHeaders() },
  )
  if (!res.ok) {
    throw new Error(`Error al exportar: ${res.status}`)
  }
  const blob = await res.blob()
  const ext = formato === "pdf" ? "pdf" : "xlsx"
  const safe = nombre.replace(/[^\w\s\-]/g, "").trim() || "reporte"
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `${safe}.${ext}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
