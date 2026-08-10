import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"
import type { DetalleEmpleado, HorasPorCliente } from "@/types/horasCliente"

/** Filtros de la vista. Un solo tipo, que viaja entero de la UI al service. */
export interface HorasClienteFiltros {
  mes: number
  anio: number
}

/**
 * Traducción filtros → query params. FUENTE ÚNICA: la consumen el listado y el export, que es lo
 * que hace estructuralmente imposible que un filtro quede en una sola de las dos puntas — y con
 * él, que el archivo traiga más filas de las que se ven en pantalla (invariante 1 del bloque B).
 *
 * ⚠️ La EMPRESA no viaja acá: el backend la toma del header `X-Empresa-Id`, porque es una VISTA
 * y la manda el selector del sidebar. Por eso el export tampoco la lleva como param.
 */
function queryHoras(f: HorasClienteFiltros): Record<string, string | undefined> {
  return { mes: String(f.mes), anio: String(f.anio) }
}

export function fetchHorasPorCliente(f: HorasClienteFiltros): Promise<HorasPorCliente> {
  const params = new URLSearchParams(queryHoras(f) as Record<string, string>)
  return apiFetch<HorasPorCliente>(`/api/horas-cliente?${params}`)
}

/** Exporta con los MISMOS filtros que la pantalla. */
export function exportarHorasPorCliente(
  formato: FormatoExport, f: HorasClienteFiltros,
): Promise<void> {
  return descargarArchivo("/api/horas-cliente/exportar", formato, "horas-por-cliente",
                          undefined, queryHoras(f))
}

export function fetchDetalleEmpleado(
  empleadoId: string, f: HorasClienteFiltros,
): Promise<DetalleEmpleado> {
  const params = new URLSearchParams({ empleado_id: empleadoId, ...queryHoras(f) } as Record<string, string>)
  return apiFetch<DetalleEmpleado>(`/api/horas-cliente/detalle?${params}`)
}

/**
 * Borra una carga. Es la ÚNICA corrección disponible desde esta pantalla.
 *
 * 🔴 NO hay `updateHora`, y no es que falte: `HorasService` declara los registros inmutables por
 * decisión escrita, y agregar una edición es revocarla. El costo de hacerlo está enumerado en
 * `services/horas_cliente_service.py::_QUE_FALTARIA_PARA_EDITAR`.
 */
export async function deleteCargaHoras(horaId: string): Promise<void> {
  await apiFetch<void>(`/api/horas-cliente/${horaId}`, { method: "DELETE" })
}
