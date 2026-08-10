import { fetchClientes, type ClientesFiltros } from "@/services/clientes"
import type { Cliente } from "@/types/cliente"

/**
 * Los setters del listado. Se inyectan en vez de vivir dentro del componente para que la carga
 * se pueda testear SIN renderizar: vitest corre sin jsdom, así que un `useEffect` no se ejecuta
 * y un test de componente no puede ver si el loading se apaga. Molde: `cargarProyectos.ts`.
 */
export interface EstadoListado {
  setClientes: (c: Cliente[]) => void
  setLoading: (v: boolean) => void
  setError: (m: string | null) => void
}

export const ERROR_CARGA = "No se pudieron cargar los clientes."

/**
 * Carga el catálogo y APAGA SIEMPRE el loading: éxito, error de red o respuesta sin items.
 * Nunca lanza.
 *
 * 🔴 El `finally` es la razón de ser de este módulo, no un detalle de estilo. En proyectos esa
 * línea se perdió al dividir la página (commit e3df1f9) y la pantalla quedó en skeleton para
 * siempre CON el endpoint respondiendo 200. Apagarlo dentro del `try` tampoco alcanza: el
 * camino de error deja la pantalla cargando encima del mensaje que el `catch` acaba de escribir.
 */
export async function cargarClientes(
  filtros: ClientesFiltros, estado: EstadoListado,
): Promise<void> {
  estado.setLoading(true)
  estado.setError(null)
  try {
    const data = await fetchClientes(filtros)
    // `?? []` cubre el 200 sin items: sin él la tabla revienta al leer .length y el síntoma es
    // una pantalla en blanco que tampoco dice qué pasó.
    estado.setClientes(data.items ?? [])
  } catch {
    estado.setError(ERROR_CARGA)
  } finally {
    estado.setLoading(false)
  }
}
