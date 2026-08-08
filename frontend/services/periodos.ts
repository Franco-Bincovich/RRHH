import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"
import type { Periodo, PeriodoListResponse } from "@/types/periodo"

const BASE = "/api/periodos"

/**
 * Exporta los períodos cerrados. El listado no tiene filtros propios (la empresa viaja por el
 * header, igual que en `fetchPeriodos`), así que las dos puntas traen el mismo conjunto por
 * construcción: no hay query params que puedan divergir.
 */
export function exportarPeriodos(formato: FormatoExport): Promise<void> {
  return descargarArchivo(`${BASE}/exportar`, formato, "periodos")
}

/** Módulos que se pueden cerrar. "Todos" se representa como null (modulo omitido). */
export const MODULO_LABEL: Record<string, string> = {
  ausencias: "Ausencias",
  vacaciones: "Vacaciones",
  costos: "Costos",
}

export interface CerrarPeriodoInput {
  empresa_id: string
  modulo: string | null
  desde: string
  hasta: string
}

/** Lista los períodos de la empresa activa (o de la que se pase por override). */
export function fetchPeriodos(empresaIdOverride?: string): Promise<PeriodoListResponse> {
  return apiFetch<PeriodoListResponse>(
    BASE,
    empresaIdOverride ? { headers: { "X-Empresa-Id": empresaIdOverride } } : {},
  )
}

/** Cierra un período (rango de fechas) para una empresa y módulo (null = todos). */
export function cerrarPeriodo(data: CerrarPeriodoInput): Promise<Periodo> {
  return apiFetch<Periodo>(BASE, { method: "POST", body: JSON.stringify(data) })
}

/** Reabre un período cerrado (reversible). */
export function reabrirPeriodo(id: string): Promise<Periodo> {
  return apiFetch<Periodo>(`${BASE}/${id}/reabrir`, { method: "POST" })
}
