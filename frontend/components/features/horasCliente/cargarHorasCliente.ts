import { fetchHorasPorCliente, type HorasClienteFiltros } from "@/services/horasCliente"
import type { HorasPorCliente } from "@/types/horasCliente"

/**
 * Los setters de la vista. Se inyectan en vez de vivir dentro del componente para que la carga
 * se pueda testear SIN renderizar: vitest corre sin jsdom, así que un `useEffect` no se ejecuta
 * y un test de componente no puede ver si el loading se apaga. Molde: `cargarProyectos.ts`.
 */
export interface EstadoVista {
  setDatos: (d: HorasPorCliente | null) => void
  setLoading: (v: boolean) => void
  setError: (m: string | null) => void
}

export const ERROR_CARGA = "No se pudieron cargar las horas."

/**
 * Carga la vista y APAGA SIEMPRE el loading: éxito, error de red o respuesta vacía. Nunca lanza.
 *
 * 🔴 El `finally` es la razón de ser de este módulo. En proyectos esa línea se perdió al dividir
 * la página (commit e3df1f9) y la pantalla quedó en skeleton para siempre CON el endpoint
 * respondiendo 200. Apagarlo dentro del `try` tampoco alcanza: el camino de error deja la
 * pantalla cargando encima del mensaje que el `catch` acaba de escribir.
 */
export async function cargarHorasCliente(
  filtros: HorasClienteFiltros, estado: EstadoVista,
): Promise<void> {
  estado.setLoading(true)
  estado.setError(null)
  try {
    estado.setDatos(await fetchHorasPorCliente(filtros))
  } catch {
    estado.setError(ERROR_CARGA)
  } finally {
    estado.setLoading(false)
  }
}
