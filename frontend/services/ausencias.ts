import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"
import { subirAdjunto } from "@/services/adjuntos"
import type {
  Ausencia,
  AusenciaCreate,
  AusenciaListResponse,
  AusenciaUpdate,
  TipoAusencia,
  TipoAusenciaListResponse,
  TipoAusenciaUpdate,
} from "@/types/ausencias"

/**
 * Tipos visibles para la empresa activa: los globales más los suyos.
 *
 * `incluirInactivos` lo usa SOLO la pantalla de configuración, que necesita verlos para poder
 * reactivarlos. El select del formulario de ausencias no debe ofrecer un tipo dado de baja.
 */
export async function fetchTiposAusencia(
  incluirInactivos = false,
): Promise<TipoAusenciaListResponse> {
  const qs = incluirInactivos ? "?incluir_inactivos=true" : ""
  return apiFetch<TipoAusenciaListResponse>(`/api/ausencias/tipos${qs}`)
}

export async function createTipoAusencia(nombre: string): Promise<TipoAusencia> {
  return apiFetch<TipoAusencia>("/api/ausencias/tipos", {
    method: "POST",
    body: JSON.stringify({ nombre }),
  })
}

/**
 * Edita un tipo: nombre, alta/baja lógica y si computa como ausentismo.
 *
 * 🔴 NO EXISTE UN `deleteTipoAusencia`, y no es un olvido. `solicitudes_ausencia.tipo_id` es
 * una FK sin ON DELETE: borrar un tipo en uso falla, y si no fallara se llevaría el historial.
 * La baja es `{ activo: false }` — lo saca de los selects y deja las ausencias viejas intactas.
 */
export async function updateTipoAusencia(
  id: string,
  cambios: TipoAusenciaUpdate,
): Promise<TipoAusencia> {
  return apiFetch<TipoAusencia>(`/api/ausencias/tipos/${id}`, {
    method: "PATCH",
    body: JSON.stringify(cambios),
  })
}

/**
 * Filtros del listado de ausencias. Los consumen el listado Y el export: es el mismo tipo a
 * propósito, para que un filtro nuevo no pueda quedar en uno solo de los dos.
 *
 * `fechaDesde`/`fechaHasta` acotan por SOLAPAMIENTO con el rango, no por contención: una
 * ausencia que empieza antes del rango pero lo cruza ENTRA. La semántica vive en el backend
 * (repositories/_rango_fechas.py) y acá no se reimplementa nada — el filtro es server-side.
 */
export interface AusenciasFiltros {
  empresaIdOverride?: string
  areaId?: string
  tipoId?: string
  empleadoId?: string
  fechaDesde?: string
  fechaHasta?: string
  /** Empleados asignados a ese proyecto (semántica en el backend, _scope_filtros). */
  proyectoId?: string
}

/** Traducción filtros → query params. Fuente ÚNICA compartida por listado y export. */
function queryAusencias(f: AusenciasFiltros): Record<string, string | undefined> {
  return {
    area_id: f.areaId,
    empleado_id: f.empleadoId,
    tipo_id: f.tipoId,
    fecha_desde: f.fechaDesde,
    fecha_hasta: f.fechaHasta,
    proyecto_id: f.proyectoId,
  }
}

export async function fetchAusencias(
  filtros: AusenciasFiltros = {},
  page = 1,
  pageSize = 20,
): Promise<AusenciaListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  for (const [k, v] of Object.entries(queryAusencias(filtros))) {
    if (v) params.set(k, v)
  }
  return apiFetch<AusenciaListResponse>(
    `/api/ausencias?${params}`,
    filtros.empresaIdOverride ? { headers: { "X-Empresa-Id": filtros.empresaIdOverride } } : {},
  )
}

export async function createAusencia(data: AusenciaCreate): Promise<Ausencia> {
  return apiFetch<Ausencia>("/api/ausencias", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

/**
 * Alta de ausencia con adjuntos diferidos. Crea primero la ausencia y, con el id nuevo,
 * sube los archivos pendientes uno por uno reusando `subirAdjunto` (mismo endpoint que
 * el alta directa). No revierte: si la ausencia se creó, existe. Devuelve la ausencia y
 * cuántos adjuntos fallaron (0 = todo ok) para que la UI avise sin bloquear.
 */
export async function crearAusenciaConAdjuntos(
  data: AusenciaCreate, files: File[],
): Promise<{ ausencia: Ausencia; fallidos: number }> {
  const ausencia = await createAusencia(data)
  let fallidos = 0
  for (const file of files) {
    try {
      await subirAdjunto("ausencia", ausencia.id, file)
    } catch {
      fallidos++
    }
  }
  return { ausencia, fallidos }
}

export async function updateAusencia(id: string, data: AusenciaUpdate): Promise<Ausencia> {
  return apiFetch<Ausencia>(`/api/ausencias/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

export async function deleteAusencia(id: string): Promise<void> {
  await apiFetch<{ ok: boolean }>(`/api/ausencias/${id}`, { method: "DELETE" })
}

/** Exporta el listado de ausencias con los MISMOS filtros que el listado. */
export function exportarAusencias(
  formato: FormatoExport,
  filtros: AusenciasFiltros = {},
): Promise<void> {
  const headers = filtros.empresaIdOverride ? { "X-Empresa-Id": filtros.empresaIdOverride } : undefined
  return descargarArchivo("/api/ausencias/exportar", formato, "ausencias", headers, queryAusencias(filtros))
}
