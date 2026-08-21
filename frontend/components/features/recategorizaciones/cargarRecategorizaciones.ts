import {
  fetchRecategorizaciones, type RecategorizacionesFiltros,
} from "@/services/recategorizaciones"
import type { Recategorizacion } from "@/types/recategorizacion"

/**
 * La carga de la planilla, con los setters inyectados en vez de dentro del componente: vitest
 * corre sin jsdom, así que un `useEffect` no se ejecuta y un test de componente no puede ver
 * ninguno de los tres desenlaces. Molde: `cargarClientes.ts`.
 */
export interface EstadoListado {
  setItems: (r: Recategorizacion[]) => void
  /**
   * ═══════════════════════════════════════════════════════════════════════════════════════
   * 🔴 EL TOTAL SALE DE `data.total`, NUNCA DE `items.length`.
   * ═══════════════════════════════════════════════════════════════════════════════════════
   * `total` es el conteo REAL del filtro (`count="exact"` del backend); `items` es UNA PÁGINA de
   * 20. Contar la página hace que el encabezado y el pie digan "20 recategorizaciones" habiendo
   * 340, y —peor— que el paginador calcule una sola página y esconda las otras 16 sin ningún
   * error a la vista.
   *
   * No es hipotético en este repo: `HorasTab` decía "9 h" con 400 h cargadas porque sumaba con
   * `.reduce()` sobre la página en lugar de leer el total del backend. Es la misma clase de bug
   * y el mismo arreglo.
   */
  setTotal: (n: number) => void
  setLoading: (v: boolean) => void
  setError: (v: boolean) => void
}

/**
 * Carga una página y APAGA SIEMPRE el loading: éxito, error de red o respuesta sin items.
 * Nunca lanza.
 *
 * 🔴 El `finally` es la razón de ser de este módulo. Esa línea se perdió una vez al dividir la
 * página de proyectos y la pantalla quedó en skeleton para siempre CON el endpoint respondiendo
 * 200. Apagarlo dentro del `try` tampoco alcanza: el camino de error deja la pantalla cargando
 * encima del mensaje que el `catch` acaba de escribir.
 */
export async function cargarRecategorizaciones(
  filtros: RecategorizacionesFiltros, page: number, pageSize: number, estado: EstadoListado,
): Promise<void> {
  estado.setLoading(true)
  estado.setError(false)
  try {
    const data = await fetchRecategorizaciones(filtros, page, pageSize)
    // `?? []` cubre el 200 sin items: sin él la tabla revienta al leer .length y el síntoma es
    // una pantalla en blanco que tampoco dice qué pasó.
    estado.setItems(data.items ?? [])
    estado.setTotal(data.total ?? 0)
  } catch {
    estado.setError(true)
  } finally {
    estado.setLoading(false)
  }
}
