import { fetchProyectos, type ProyectosFiltros } from "@/services/proyectos"
import type { Proyecto } from "@/types/proyecto"

/**
 * Los setters del listado. Se inyectan en vez de vivir dentro del componente para que la carga
 * se pueda testear sin renderizar: vitest corre SIN jsdom, así que un `useEffect` no se ejecuta
 * y un test de componente NO puede ver si el loading se apaga. Es el caso #4 de "un test solo
 * prueba lo que el fake puede desmentir": el fake tiene que poder desmentir el `finally`.
 */
export interface EstadoListado {
  setProyectos: (p: Proyecto[]) => void
  setLoading: (v: boolean) => void
  setError: (m: string | null) => void
}

export const ERROR_CARGA = "No se pudieron cargar los proyectos."

/**
 * Carga el listado de proyectos y APAGA SIEMPRE el loading: éxito, error de red o respuesta sin
 * items. Nunca lanza.
 *
 * 🔴 El `finally` es la razón de ser de este módulo, no un detalle de estilo. Estuvo borrado
 * desde el commit e3df1f9 —donde la línea era contigua al array de dependencias del useCallback
 * y el hunk se llevó las dos— y la pantalla de proyectos quedó en skeleton para siempre, incluso
 * con el endpoint respondiendo 200. Apagarlo dentro del `try` no alcanza: el camino de error deja
 * la pantalla cargando y el usuario nunca ve el mensaje que el `catch` acaba de escribir.
 */
export async function cargarProyectos(filtros: ProyectosFiltros, estado: EstadoListado): Promise<void> {
  estado.setLoading(true)
  estado.setError(null)
  try {
    const data = await fetchProyectos(filtros)
    // `?? []` cubre el 200 sin items: sin él la grilla revienta al leer .length y el síntoma
    // sería una pantalla en blanco, otra vez sin decir qué pasó.
    estado.setProyectos(data.items ?? [])
  } catch {
    estado.setError(ERROR_CARGA)
  } finally {
    estado.setLoading(false)
  }
}
