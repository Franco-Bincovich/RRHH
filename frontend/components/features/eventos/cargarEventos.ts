import { fetchEventos, type EventosFiltros } from "@/services/eventos"
import type { Evento } from "@/types/evento"

/**
 * Los setters del listado. Se inyectan en vez de vivir dentro del componente para que la carga
 * se pueda testear SIN renderizar: vitest corre sin jsdom, así que un `useEffect` no se ejecuta
 * y un test de componente no puede ver si el loading se apaga. Molde: `cargarClientes.ts`.
 */
export interface EstadoListado {
  setEventos: (e: Evento[]) => void
  setTotal: (n: number) => void
  setLoading: (v: boolean) => void
  setError: (m: string | null) => void
}

export const ERROR_CARGA = "No se pudieron cargar los recordatorios."

/**
 * Carga una página de la agenda y APAGA SIEMPRE el loading: éxito, error de red o respuesta sin
 * items. Nunca lanza.
 *
 * 🔴 El `finally` es la razón de ser de este módulo, no un detalle de estilo. En proyectos esa
 * línea se perdió al dividir la página y la pantalla quedó en skeleton para siempre CON el
 * endpoint respondiendo 200.
 *
 * ⚠️ `total` sale del backend, NO de `items.length`: es el total del filtro sin paginar, y es lo
 * que la barra de paginación necesita para saber cuántas páginas hay. Pasarle el largo de la
 * página haría que diga siempre "1 de 1" sin ningún error visible.
 */
export async function cargarEventos(
  filtros: EventosFiltros, page: number, pageSize: number, estado: EstadoListado,
): Promise<void> {
  estado.setLoading(true)
  estado.setError(null)
  try {
    const data = await fetchEventos(filtros, page, pageSize)
    // `?? []` cubre el 200 sin items: sin él la tabla revienta al leer .length y el síntoma es
    // una pantalla en blanco que tampoco dice qué pasó.
    estado.setEventos(data.items ?? [])
    estado.setTotal(data.total ?? 0)
  } catch {
    estado.setError(ERROR_CARGA)
  } finally {
    estado.setLoading(false)
  }
}
