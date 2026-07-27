/**
 * Barra de filtros genérica, presentacional y controlada. Cada campo trae su propio
 * `onChange`: la página conserva su estado (useState), su fetch y su debounce — este
 * componente SOLO renderiza los controles con label visible (patrón AuditFilters, doc
 * UX-UI.md). No fetchea, no debouncea, no tiene estado propio.
 *
 * 5 tipos de control:
 *   select      · una opción de una lista ya resuelta por la página
 *   search      · texto libre (la página debouncea, no este componente)
 *   date        · una fecha suelta
 *   daterange   · rango desde/hasta, emitido como un solo objeto
 *   multiselect · varias opciones a la vez, como checkboxes
 *
 * Por qué `multiselect` son checkboxes y no un `<select multiple>`: el nativo exige
 * ctrl/cmd+click para elegir más de uno, que es justo lo que un usuario no descubre solo.
 * Con pocas opciones (área, estado, tipo) los checkboxes se ven y se usan. Si algún filtro
 * llega a tener decenas de opciones, eso pide un combobox con búsqueda — control distinto,
 * no un ajuste de este.
 *
 * El molde para el hook que alimenta esta barra está en components/features/shared/filtros.ts.
 */

export type OpcionFiltro = { value: string; label: string }
export type RangoFechas = { desde: string; hasta: string }

export type FiltroCampo = { label: string } & (
  | { tipo: "select"; value: string; onChange: (v: string) => void; opciones: OpcionFiltro[]; opcionTodos?: string }
  | { tipo: "search"; value: string; onChange: (v: string) => void; placeholder?: string }
  | { tipo: "date"; value: string; onChange: (v: string) => void }
  | { tipo: "daterange"; value: RangoFechas; onChange: (v: RangoFechas) => void }
  | { tipo: "multiselect"; value: string[]; onChange: (v: string[]) => void; opciones: OpcionFiltro[] }
)

interface FiltersBarProps {
  campos: FiltroCampo[]
}

const FIELD_CLASS =
  "min-h-11 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

const LABEL_CLASS = "flex flex-col gap-1 text-xs text-muted-foreground"

/**
 * Agrega o saca un valor de la selección. Devuelve un array nuevo (no muta).
 * Exportada para poder testear la propagación del multiselect sin un DOM: es la única
 * lógica no trivial del componente.
 */
export function alternar(seleccion: string[], value: string): string[] {
  return seleccion.includes(value) ? seleccion.filter((v) => v !== value) : [...seleccion, value]
}

function Campo({ campo }: { campo: FiltroCampo }) {
  switch (campo.tipo) {
    case "select":
      return (
        <select className={FIELD_CLASS} value={campo.value} onChange={(e) => campo.onChange(e.target.value)}>
          <option value="">{campo.opcionTodos ?? "Todos"}</option>
          {campo.opciones.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      )
    case "date":
      return (
        <input type="date" className={FIELD_CLASS} value={campo.value} onChange={(e) => campo.onChange(e.target.value)} />
      )
    case "daterange":
      return (
        <div className="flex items-center gap-2">
          <input
            type="date" className={FIELD_CLASS} value={campo.value.desde} aria-label={`${campo.label} — desde`}
            onChange={(e) => campo.onChange({ ...campo.value, desde: e.target.value })}
          />
          <span aria-hidden="true" className="text-muted-foreground">–</span>
          <input
            type="date" className={FIELD_CLASS} value={campo.value.hasta} aria-label={`${campo.label} — hasta`}
            onChange={(e) => campo.onChange({ ...campo.value, hasta: e.target.value })}
          />
        </div>
      )
    case "multiselect":
      return (
        <div className="flex min-h-11 flex-wrap items-center gap-x-3 gap-y-1" role="group" aria-label={campo.label}>
          {campo.opciones.map((o) => (
            <label key={o.value} className="flex items-center gap-1.5 text-sm text-foreground">
              <input
                type="checkbox" className="size-4 rounded border-input"
                checked={campo.value.includes(o.value)}
                onChange={() => campo.onChange(alternar(campo.value, o.value))}
              />
              {o.label}
            </label>
          ))}
        </div>
      )
    default:
      return (
        <input
          type="search" className={FIELD_CLASS} value={campo.value}
          placeholder={campo.placeholder} onChange={(e) => campo.onChange(e.target.value)}
        />
      )
  }
}

export function FiltersBar({ campos }: FiltersBarProps) {
  return (
    <div className="mb-4 flex flex-wrap items-end gap-3">
      {campos.map((campo) =>
        // daterange y multiselect renderizan VARIOS controles, así que su etiqueta va como
        // texto: un <label> no puede apuntar a más de un control, y envolverlos a todos haría
        // que un lector de pantalla anuncie la etiqueta en cada uno.
        campo.tipo === "daterange" || campo.tipo === "multiselect" ? (
          <div key={campo.label} className={LABEL_CLASS}>
            <span>{campo.label}</span>
            <Campo campo={campo} />
          </div>
        ) : (
          <label key={campo.label} className={LABEL_CLASS}>
            {campo.label}
            <Campo campo={campo} />
          </label>
        ),
      )}
    </div>
  )
}
