import type { FiltroCampo } from "@/components/ui/FiltersBar"
import type { FiltroClasificacion } from "@/types/candidato"

/**
 * Armado del array de <FiltersBar> para /candidatos. Aparte de la página por lo mismo que en las
 * otras pantallas del bloque: **es lo único que un test puede ejercitar sin DOM**, así que los
 * chips se prueban contra el cableado real y no contra campos inventados.
 *
 * 🔴 ACÁ NO HAY NINGÚN FILTRO AVANZADO, Y ESO ES UNA DECISIÓN. La pantalla tiene DOS filtros. La
 * regla del patrón —"la fila superior es buscador, selectores y un 'Más filtros' para el resto"—
 * existe para que una fila de siete controles no tape la tabla; con dos, esconder uno atrás de un
 * botón deja la mitad de la pantalla inalcanzable a cambio de nada.
 *
 * 🔴 "SIN BÚSQUEDA ASIGNADA" DEJÓ DE SER UN CHECKBOX Y PASÓ A SER UN SELECT, y no es cosmética:
 * los chips se derivan de los `FiltroCampo`, y el patrón tiene cinco tipos de control (select,
 * search, date, daterange, multiselect) — **ninguno es un checkbox**. Con el tilde, ese filtro
 * quedaba activo SIN chip: la pantalla mostraba 4 de 31 candidatos y el único indicio de por qué
 * era una casilla tildada arriba, fuera del panel. El select dice lo mismo y se puede quitar por
 * los dos caminos (el control y la ✕ del chip).
 *
 * ⚠️ Y ES BINARIO, no tri-estado como el "Superior" de /empleados: el backend recibe
 * `sin_vacante: bool` y `false` significa "todas", no "solo las que TIENEN búsqueda". Ofrecer esa
 * tercera opción sería un filtro que el backend no puede honrar.
 *
 * Sin estado ni efectos: recibe valores y setters, devuelve la descripción de los controles. El
 * reset de página lo dispara `onFiltroChange` en cada onChange (invariante 4 del bloque B).
 */
export const ASIGNACION_OPCIONES = [
  { value: "sin", label: "Sin búsqueda asignada" },
]

/**
 * ⚠️ `no_relevante` está en la lista como una más y NO se oculta ni se colapsa por defecto: la
 * opción por defecto es "todas". Esconder los no relevantes convertiría el filtro en la decisión
 * que este módulo justamente no toma — ver `LeyendaDescarte`.
 */
export const CLASIFICACION_OPCIONES: { value: FiltroClasificacion; label: string }[] = [
  { value: "relevante", label: "Relevante" },
  { value: "dudoso", label: "Dudoso" },
  { value: "no_relevante", label: "No relevante" },
  { value: "sin_clasificar", label: "Sin clasificar" },
]

export interface ArgsCamposCandidatos {
  asignacionFiltro: string
  setAsignacionFiltro: (v: string) => void
  clasificacion: string
  setClasificacion: (v: string) => void
  onFiltroChange: () => void
}

export function construirCampos(a: ArgsCamposCandidatos): FiltroCampo[] {
  return [
    { tipo: "select" as const, label: "Asignación", value: a.asignacionFiltro, opcionTodos: "Todos los candidatos",
      onChange: (v: string) => { a.setAsignacionFiltro(v); a.onFiltroChange() }, opciones: ASIGNACION_OPCIONES },
    { tipo: "select" as const, label: "Clasificación", value: a.clasificacion, opcionTodos: "Todas las clasificaciones",
      onChange: (v: string) => { a.setClasificacion(v); a.onFiltroChange() }, opciones: CLASIFICACION_OPCIONES },
  ]
}
