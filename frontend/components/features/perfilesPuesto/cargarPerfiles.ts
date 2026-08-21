import { fetchCamposPerfil, fetchPerfiles, type PerfilesFiltros } from "@/services/perfilesPuesto"
import type { CamposPerfilResponse, PerfilPuesto } from "@/types/perfilPuesto"

/**
 * Las DOS cargas de la pantalla, con sus setters inyectados en vez de vivir dentro del
 * componente: vitest corre sin jsdom, así que un `useEffect` no se ejecuta y un test de
 * componente no puede ver si el loading se apaga. Molde: `cargarClientes.ts`.
 *
 * 🔴 EL `finally` ES LA RAZÓN DE SER DE ESTE MÓDULO, no un detalle de estilo. Esa línea se
 * perdió una vez al dividir la página de proyectos y la pantalla quedó en skeleton para siempre
 * CON el endpoint respondiendo 200. Apagarlo dentro del `try` tampoco alcanza: el camino de
 * error deja la pantalla cargando encima del mensaje que el `catch` acaba de escribir.
 */

export interface EstadoListado {
  setPerfiles: (p: PerfilPuesto[]) => void
  setTotal: (n: number) => void
  setLoading: (v: boolean) => void
  setError: (m: string | null) => void
}

export const ERROR_CARGA = "No se pudieron cargar los perfiles de puesto."

/** Carga una página del catálogo y APAGA SIEMPRE el loading. Nunca lanza. */
export async function cargarPerfiles(
  filtros: PerfilesFiltros, page: number, pageSize: number, estado: EstadoListado,
): Promise<void> {
  estado.setLoading(true)
  estado.setError(null)
  try {
    const data = await fetchPerfiles(filtros, page, pageSize)
    // `?? []` cubre el 200 sin items: sin él la grilla revienta al leer .length y el síntoma es
    // una pantalla en blanco que tampoco dice qué pasó.
    estado.setPerfiles(data.items ?? [])
    estado.setTotal(data.total ?? 0)
  } catch {
    estado.setError(ERROR_CARGA)
  } finally {
    estado.setLoading(false)
  }
}

/**
 * Carga el catálogo de campos del formulario.
 *
 * ⚠️ SU FALLA NO ROMPE LA PANTALLA, a diferencia de la del listado: sin `/campos` las tarjetas
 * se siguen viendo (muestran el valor crudo del nivel y la modalidad en vez de su etiqueta) y lo
 * único que no se puede es ABRIR EL FORMULARIO — que sin labels, sin ayudas y sin vocabularios no
 * sería un formulario a medias sino uno que guarda mal. Por eso devuelve `null` en vez de lanzar,
 * y quien decide qué hacer con eso es la pantalla.
 */
export async function cargarCampos(): Promise<CamposPerfilResponse | null> {
  try {
    return await fetchCamposPerfil()
  } catch {
    return null
  }
}
