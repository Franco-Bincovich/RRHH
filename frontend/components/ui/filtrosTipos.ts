/**
 * Los tipos de la barra de filtros. Viven aparte de `FiltersBar.tsx` para que los tres módulos
 * del patrón —el render de un control (`FiltrosCampo.tsx`), la derivación de los chips
 * (`filtrosChips.ts`) y la barra (`FiltersBar.tsx`)— puedan importarlos sin un ciclo entre sí.
 * `FiltersBar` los RE-EXPORTA: los 17 importadores que hacen
 * `import type { FiltroCampo } from "@/components/ui/FiltersBar"` siguen funcionando igual.
 *
 * 5 tipos de control:
 *   select      · una opción de una lista ya resuelta por la página
 *   search      · texto libre (la página debouncea, no este componente)
 *   date        · una fecha suelta
 *   daterange   · rango desde/hasta, emitido como un solo objeto
 *   multiselect · varias opciones a la vez, como checkboxes
 */

export type OpcionFiltro = { value: string; label: string }
export type RangoFechas = { desde: string; hasta: string }

/**
 * `avanzado` manda el campo detrás del "Más filtros" del patrón (sistema de diseño §3: la fila
 * superior es buscador + selectores, "y un 'Más filtros' para el resto"). Es OPCIONAL y por
 * default `false`, así que un campo que no lo declara queda a la vista: las 7 pantallas que ya
 * usaban `FiltersBar` no cambian de forma por existir esta propiedad.
 *
 * 🔴 Quién es avanzado lo decide CADA PANTALLA, no `FiltersBar` adivinando por posición. Un
 * componente que escondiera "del tercero en adelante" dejaría el filtro más usado de una pantalla
 * atrás de un botón y el menos usado a la vista, sin que nadie lo haya decidido.
 */
export type FiltroCampo = { label: string; avanzado?: boolean } & (
  | { tipo: "select"; value: string; onChange: (v: string) => void; opciones: OpcionFiltro[]; opcionTodos?: string }
  | { tipo: "search"; value: string; onChange: (v: string) => void; placeholder?: string }
  | { tipo: "date"; value: string; onChange: (v: string) => void }
  | { tipo: "daterange"; value: RangoFechas; onChange: (v: RangoFechas) => void }
  | { tipo: "multiselect"; value: string[]; onChange: (v: string[]) => void; opciones: OpcionFiltro[] }
)
