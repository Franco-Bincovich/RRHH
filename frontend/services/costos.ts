import type { DashboardCostos, Nomina, NominaCreate, Presupuesto, PresupuestoCreate } from "@/types/costo"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

export async function fetchDashboardCostos(mes: number, anio: number): Promise<DashboardCostos> {
  return apiFetch<DashboardCostos>(`/api/costos/dashboard?mes=${mes}&anio=${anio}`)
}

/**
 * Traducción del período → query params. Fuente ÚNICA compartida por listado y export: el
 * período ES el filtro de nómina, así que sale de un solo lugar para los dos
 * (invariante list ↔ export).
 */
function queryNomina(mes: number, anio: number): Record<string, string | undefined> {
  return { mes: String(mes), anio: String(anio) }
}

export async function fetchNominaMes(mes: number, anio: number): Promise<Nomina[]> {
  const q = new URLSearchParams(queryNomina(mes, anio) as Record<string, string>)
  return apiFetch<Nomina[]>(`/api/costos/nomina?${q}`)
}

/** Exporta la nómina del período con los MISMOS filtros que el listado. */
export function exportarNomina(formato: FormatoExport, mes: number, anio: number): Promise<void> {
  return descargarArchivo(
    "/api/costos/nomina/exportar", formato, "nomina", undefined, queryNomina(mes, anio),
  )
}

export async function cargarNomina(data: NominaCreate): Promise<Nomina> {
  return apiFetch<Nomina>("/api/costos/nomina", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function setPresupuesto(data: PresupuestoCreate): Promise<Presupuesto> {
  return apiFetch<Presupuesto>("/api/costos/presupuesto", {
    method: "POST",
    body: JSON.stringify(data),
  })
}
