import { apiFetch, descargarArchivo } from "./api"

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

/**
 * Baja un reporte YA generado.
 *
 * 🔴 USA `descargarArchivo`, el mismo helper que los otros 26 exports del sistema. Antes tenía
 * su propia copia con `fetch` crudo + `authHeaders()`, y esa copia **no pasaba por el
 * interceptor de refresh**: con el access token vencido —una pestaña abierta un rato— los 26
 * exports del resto del sistema renovaban el token solos y éste tiraba un error genérico
 * ("No se pudo exportar"). Era la única pantalla de descarga que se comportaba distinto, y
 * duplicaba además la construcción del nombre de archivo y la extensión.
 */
export function exportarReporte(
  id: string,
  formato: "pdf" | "excel",
  nombre: string,
): Promise<void> {
  return descargarArchivo(`/api/reportes/${id}/exportar`, formato, nombre)
}

/**
 * Genera el reporte Y LO BAJA. Es lo que hace el botón del catálogo.
 *
 * 🔴 POR QUÉ EXISTE. El catálogo tenía un único botón "Generar" que llamaba sólo a
 * `generarReporte`: dejaba una fila en el historial de más abajo, mostraba "generado
 * exitosamente" y **no bajaba ningún archivo**. La pantalla se presenta como "Generá reportes
 * estándar descargables en PDF o Excel", así que el usuario apretaba, leía el cartel de éxito
 * y no encontraba nada: para tener el archivo había que bajar hasta el historial, ubicar la
 * fila entre las demás y apretar un segundo botón sin texto. Medido el 23/8/2026: 10 reportes
 * generados en 28 segundos y cero descargas.
 */
export async function generarYDescargar(
  body: ReporteGenerarRequest,
  formato: "pdf" | "excel",
): Promise<ReporteResponse> {
  const reporte = await generarReporte(body)
  await exportarReporte(reporte.id, formato, reporte.nombre)
  return reporte
}
