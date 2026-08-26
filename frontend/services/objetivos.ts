import type {
  CambiarEstadoRequest, Objetivo, ObjetivoCreate, ObjetivoListResponse, ObjetivoUpdate,
  TipoObjetivo, UserItem,
} from "@/types/objetivo"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

const BASE = "/api/objetivos"

export type { FormatoExport }

/**
 * Filtros del listado de objetivos. Los consumen el listado Y el export: es el MISMO tipo a
 * propósito, para que un filtro nuevo no pueda quedar en uno solo de los dos (invariante 2 del
 * bloque B). Molde: `VacacionesFiltros` / `AusenciasFiltros`.
 *
 * 🔴 ESTO ERA CUATRO POSICIONALES Y POR ESO SE CAMBIÓ. `fetchObjetivos(empresa, estado,
 * responsable, prioridad)` ya tenía cuatro `string | undefined` en fila, y sumarle `tipo` daba
 * CINCO: el corrimiento silencioso de argumentos que el bloque B pagó en vacaciones y ausencias
 * —un argumento corrido no da error, da el conjunto equivocado—. Es exactamente el mismo cambio
 * que el backend ya hizo del lado suyo con `ObjetivosFiltros` (schemas/objetivo_filtros.py), y
 * por eso el objeto se llama igual a los dos lados.
 *
 * 🔴 `periodicidad` y `area` ENTRARON EL 25/8/2026 (bloque N8). Estaban implementados de punta a
 * punta en el backend —`ObjetivosFiltros`, el router, `_objetivo_filtros.aplicar_filtros` y hasta
 * un endpoint propio de catálogo, `/api/objetivos/areas-conocidas`, con CERO llamadores— y
 * ninguna pantalla los ofrecía. El comentario que estaba acá decía justamente eso ("agregarlos es
 * sumar un campo y una línea"); esto es esa línea.
 *
 * ⚠️ `area` NO es el área del RESPONSABLE. Filtra por `objetivos.areas_involucradas`, que es un
 * array de texto del objetivo mismo (migración 119): "¿qué objetivos tocan a Sistemas?". La
 * decisión de producto que dice que objetivos no se corta por área se refiere a la otra —los
 * responsables son usuarios de Capital Humano y no tienen área—, y sigue en pie.
 */
export interface ObjetivosFiltros {
  empresaIdOverride?: string
  estado?: string
  responsableId?: string
  prioridad?: string
  /** A cuál de las dos vistas (anual / operativo) se acota. `undefined` = las dos. */
  tipo?: TipoObjetivo
  /** Un área de `areas_involucradas` (texto, no id). El backend pregunta si el array la contiene. */
  area?: string
  /** Texto libre del objetivo ("mensual", "por sprint"): el backend compara por igualdad. */
  periodicidad?: string
}

/** Traducción filtros → query params. Fuente ÚNICA compartida por listado y export. */
function queryObjetivos(f: ObjetivosFiltros): Record<string, string | undefined> {
  return {
    estado: f.estado,
    responsable_id: f.responsableId,
    prioridad: f.prioridad,
    tipo: f.tipo,
    area: f.area,
    periodicidad: f.periodicidad,
  }
}

function override(id?: string): RequestInit {
  return id ? { headers: { "X-Empresa-Id": id } } : {}
}

export function exportarObjetivos(formato: FormatoExport, filtros: ObjetivosFiltros = {}): Promise<void> {
  const headers = filtros.empresaIdOverride ? { "X-Empresa-Id": filtros.empresaIdOverride } : undefined
  return descargarArchivo(`${BASE}/exportar`, formato, "objetivos", headers, queryObjetivos(filtros))
}

export async function fetchObjetivos(filtros: ObjetivosFiltros = {}): Promise<ObjetivoListResponse> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(queryObjetivos(filtros))) {
    if (v) params.set(k, v)
  }
  const q = params.size ? `?${params}` : ""
  return apiFetch<ObjetivoListResponse>(`${BASE}${q}`, override(filtros.empresaIdOverride))
}

/**
 * El vocabulario cerrado de `tipo`, con su etiqueta legible, servido por el backend.
 *
 * 🔴 NO SE DERIVA EN EL FRONT. Los dos `value` son el literal del CHECK de la migración 119 y del
 * `Literal` de Pydantic; una copia local que derive ofrecería en el selector un valor que el
 * backend rechaza con 422. El endpoint existe para eso — ver el docstring de
 * `routers/objetivos_catalogos.py::campos_objetivo`. Mismo criterio que provincias y que los
 * campos de perfil de puesto.
 */
/**
 * Las áreas ya usadas en algún objetivo, para el desplegable del filtro.
 *
 * 🔴 EL VOCABULARIO SON LOS DATOS, no una constante. `areas_involucradas` es texto libre por
 * decisión de producto, así que las opciones tienen que salir de la base — por eso el backend le
 * dio endpoint propio en vez de meterlo en `/campos`, que sirve un vocabulario CERRADO y
 * cacheable. El porqué del corte está escrito en `routers/objetivos_catalogos.py`.
 *
 * Devuelve `[]` mientras nadie haya cargado un área, y entonces el filtro no se dibuja.
 */
export async function fetchAreasConocidas(): Promise<string[]> {
  return apiFetch<string[]>(`${BASE}/areas-conocidas`)
}

export async function fetchCamposObjetivo(): Promise<{ tipos: { value: TipoObjetivo; label: string }[] }> {
  return apiFetch<{ tipos: { value: TipoObjetivo; label: string }[] }>(`${BASE}/campos`)
}

export async function createObjetivo(data: ObjetivoCreate): Promise<Objetivo> {
  return apiFetch<Objetivo>(BASE, { method: "POST", body: JSON.stringify(data) })
}

export async function updateObjetivo(id: string, data: ObjetivoUpdate): Promise<Objetivo> {
  return apiFetch<Objetivo>(`${BASE}/${id}`, { method: "PUT", body: JSON.stringify(data) })
}

export async function cambiarEstadoObjetivo(id: string, data: CambiarEstadoRequest): Promise<Objetivo> {
  return apiFetch<Objetivo>(`${BASE}/${id}/estado`, { method: "PUT", body: JSON.stringify(data) })
}

export async function deleteObjetivo(id: string): Promise<void> {
  await apiFetch<{ ok: boolean }>(`${BASE}/${id}`, { method: "DELETE" })
}

export async function fetchUsuariosActivos(): Promise<{ items: UserItem[]; total: number }> {
  return apiFetch<{ items: UserItem[]; total: number }>("/api/usuarios")
}
