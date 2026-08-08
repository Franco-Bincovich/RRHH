import { API_BASE, apiFetch, authHeaders, descargarArchivo, type FormatoExport } from "@/services/api"
import type { Empresa, EmpresaCreate, EmpresaListResponse, EmpresaUpdate } from "@/types/empresa"

const BASE = "/api/empresas"

export async function fetchEmpresas(): Promise<EmpresaListResponse> {
  return apiFetch<EmpresaListResponse>(BASE)
}

/**
 * Exporta el listado de empresas — las MISMAS filas que muestra la pantalla.
 *
 * `fetchEmpresas` no manda ningún query param, y este tampoco: no hay filtros que puedan
 * quedar en una sola de las dos puntas. 🔴 El día que el listado gane uno (por ejemplo
 * activas/inactivas), NO se lo agregue a una sola: los dos tienen que armar sus params con
 * UNA función de traducción compartida (molde: `queryProyectos` en services/proyectos.ts).
 *
 * Tampoco viaja `X-Empresa-Id`: esta pantalla lista TODAS las empresas, no las de la activa.
 */
export function exportarEmpresas(formato: FormatoExport): Promise<void> {
  return descargarArchivo(`${BASE}/exportar`, formato, "empresas")
}

export async function fetchEmpresa(id: string): Promise<Empresa> {
  return apiFetch<Empresa>(`${BASE}/${id}`)
}

export async function createEmpresa(data: EmpresaCreate): Promise<Empresa> {
  return apiFetch<Empresa>(BASE, { method: "POST", body: JSON.stringify(data) })
}

export async function updateEmpresa(id: string, data: EmpresaUpdate): Promise<Empresa> {
  return apiFetch<Empresa>(`${BASE}/${id}`, { method: "PUT", body: JSON.stringify(data) })
}

export async function toggleEmpresaActiva(id: string, activa: boolean): Promise<Empresa> {
  return apiFetch<Empresa>(`${BASE}/${id}/activa`, {
    method: "PATCH",
    body: JSON.stringify({ activa }),
  })
}

export async function uploadLogo(id: string, file: File): Promise<Empresa> {
  const form = new FormData()
  form.append("file", file)
  const headers = authHeaders()
  // Omitir Content-Type para que el browser setee el boundary multipart
  delete headers["Content-Type"]
  const res = await fetch(`${API_BASE}${BASE}/${id}/logo`, {
    method: "POST",
    headers,
    body: form,
  })
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { message?: string }
    throw new Error(body.message ?? "Error al subir el logo")
  }
  return res.json() as Promise<Empresa>
}
