import type {
  Empleado, EmpleadoCreate, EmpleadoListResponse, EmpleadoSeleccionable, EmpleadoUpdate,
  OrdenEmpleados,
} from "@/types/empleado"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

/**
 * Filtros del listado de empleados, compartidos por `fetchEmpleados` y `exportarEmpleados`
 * con los MISMOS nombres a propósito: antes eran cuatro posicionales `string | undefined`
 * en distinto orden entre las dos, así que copiar argumentos de una a la otra compilaba
 * igual y mandaba el filtro equivocado al backend.
 *
 * `empresaId` viaja por header `X-Empresa-Id` (el valor "todas" el backend lo interpreta
 * como consolidado); el resto van como query params.
 *
 * `esLider` es un booleano de tres estados: `undefined` = sin filtro, `true` = solo líderes,
 * `false` = solo no-líderes. Por eso NO se puede normalizar con `|| undefined` como los
 * strings: `false` es un filtro válido, no un vacío.
 */
export interface EmpleadosFiltros {
  search?: string
  estado?: string
  empresaId?: string
  areaId?: string
  esLider?: boolean
  /** Empleados asignados a ese proyecto (semántica en el backend, _scope_filtros). */
  proyectoId?: string
  /**
   * Tri-estado como `esLider`: `undefined` = sin filtro, `true` = sin superior asignado,
   * `false` = con superior. Es el destino al que linkea la alerta agregada del dashboard
   * (`/empleados?sin_manager=true`), así que el nombre del query param es parte del contrato.
   */
  sinManager?: boolean
  /**
   * El ORDEN del listado. `undefined` = el de siempre (apellido, nombre, id).
   *
   * 🔴 VA EN `EmpleadosFiltros` —y no como argumento aparte— justamente porque NO es un filtro:
   * así el export lo recibe por el mismo canal y el archivo sale en el mismo orden que la
   * pantalla. La invariante del bloque B ("el MISMO tipo lo consumen el listado y el export")
   * vale igual para el orden: un archivo ordenado distinto de lo que se ve es la misma clase de
   * divergencia que un filtro que solo viaja en uno de los dos.
   *
   * Lo usan las dos pantallas del ciclo de vida: `/proximos-ingresos` pide `fecha_ingreso_asc`
   * (quién entra primero) y `/bajas` pide `fecha_egreso_desc` (quién se fue último).
   */
  orden?: OrdenEmpleados
}

export async function fetchEmpleados(
  opts: EmpleadosFiltros & { page: number; pageSize: number },
): Promise<EmpleadoListResponse> {
  const { page, pageSize, search, estado, empresaId, areaId, esLider, proyectoId, sinManager, orden } = opts
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (search) params.set("search", search)
  if (estado) params.set("estado", estado)
  if (areaId) params.set("area_id", areaId)
  if (esLider !== undefined) params.set("es_lider", String(esLider))
  if (proyectoId) params.set("proyecto_id", proyectoId)
  if (sinManager !== undefined) params.set("sin_manager", String(sinManager))
  if (orden) params.set("orden", orden)
  return apiFetch<EmpleadoListResponse>(
    `/api/empleados?${params}`,
    empresaId ? { headers: { "X-Empresa-Id": empresaId } } : {},
  )
}

/** Exporta el listado de empleados (pdf/excel/csv/word) con los filtros activos aplicados. */
export function exportarEmpleados(
  opts: EmpleadosFiltros & { formato: FormatoExport },
): Promise<void> {
  const { formato, search, estado, empresaId, areaId, esLider, proyectoId, sinManager, orden } = opts
  const headers = empresaId ? { "X-Empresa-Id": empresaId } : undefined
  return descargarArchivo("/api/empleados/exportar", formato, "empleados", headers, {
    search,
    estado,
    area_id: areaId,
    es_lider: esLider === undefined ? undefined : String(esLider),
    proyecto_id: proyectoId,
    sin_manager: sinManager === undefined ? undefined : String(sinManager),
    orden,
  })
}

export async function fetchEmpleado(id: string): Promise<Empleado> {
  return apiFetch<Empleado>(`/api/empleados/${id}`)
}

export async function createEmpleado(data: EmpleadoCreate): Promise<Empleado> {
  return apiFetch<Empleado>("/api/empleados", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function updateEmpleado(id: string, data: EmpleadoUpdate): Promise<Empleado> {
  return apiFetch<Empleado>(`/api/empleados/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

export async function fetchRolesConocidos(): Promise<string[]> {
  return apiFetch<string[]>("/api/empleados/roles-conocidos")
}

export async function fetchValoresConocidos(campo: string): Promise<string[]> {
  return apiFetch<string[]>(`/api/empleados/valores-conocidos?campo=${encodeURIComponent(campo)}`)
}

export async function fetchEmpleadosSeleccionables(
  empresaId: string,
): Promise<EmpleadoSeleccionable[]> {
  return apiFetch<EmpleadoSeleccionable[]>(
    `/api/empleados/seleccionables?empresa_id=${encodeURIComponent(empresaId)}`,
  )
}

/**
 * Pasa un empleado de `preingreso` a `activo`: el día que la persona efectivamente entró.
 *
 * Es un ACTO y no una edición de campo, y por eso tiene endpoint propio sin body — el mismo
 * criterio con el que el backend lo separó del PUT (`routers/empleados.py:62`). Un
 * `updateEmpleado(id, { estado: "activo" })` saltearía las dos guardas que este camino aplica.
 *
 * 🔴 EL MENSAJE DEL 400 SE MUESTRA TAL CUAL. `INGRESO_AUN_NO_OCURRIO` viene redactado con la
 * fecha adentro y con la salida ("corregí la fecha en el legajo y después activala"): un
 * genérico de "no se pudo activar" tira justo lo que hace falta para resolverlo. Los otros dos
 * códigos son EMPLEADO_NOT_FOUND (404) y EMPLEADO_NO_ES_PREINGRESO (409).
 */
export async function activarEmpleado(id: string): Promise<Empleado> {
  return apiFetch<Empleado>(`/api/empleados/${id}/activar`, { method: "POST" })
}
