import { Select } from "@/components/ui/select"
import type { FiltroCampo } from "@/components/ui/filtrosTipos"

/**
 * El render de UN control de la barra de filtros. Presentacional y controlado: cada campo trae
 * su propio `onChange` y la página conserva su estado, su fetch y su debounce.
 *
 * Salió de `FiltersBar.tsx` al sumarle el panel del sistema de diseño (el "Más filtros" y la fila
 * de chips): con los tres adentro el archivo pasaba el límite de 150 de un componente, y esta es
 * la mitad que NO cambió — la barra decide qué campos muestra, esto dibuja uno.
 *
 * Por qué `multiselect` son checkboxes y no un `<select multiple>`: el nativo exige ctrl/cmd+click
 * para elegir más de uno, que es justo lo que un usuario no descubre solo. Con pocas opciones
 * (área, estado, tipo) los checkboxes se ven y se usan. Si algún filtro llega a tener decenas de
 * opciones, eso pide un combobox con búsqueda — control distinto, no un ajuste de este.
 */

/*
 * Los `<input>` de la barra (fecha y búsqueda). **La altura es la MISMA fórmula que la del
 * `size="sm"` de `components/ui/select.tsx`, y tiene que seguir siéndolo:** 44px de área táctil
 * abajo de `md`, y los 30px que `docs/SISTEMA-DE-DISENO.md` §3 fija para la barra de filtros de
 * `md` para arriba.
 *
 * 🔴 POR QUÉ ESTÁ ESCRITO ACÁ Y NO SALE DE UN PRIMITIVO. Al migrar los `<select>` a `<Select>`
 * (19/8/2026) los selectores tomaron esa altura y estos inputs se quedaron en `min-h-11`, así que
 * la barra quedó con controles de 30px al lado de controles de 44px — visiblemente peor que antes
 * de unificar nada. Igualarlos acá es el arreglo mínimo; el correcto es que estos inputs pasen a
 * `components/ui/input.tsx` con la misma variante de tamaño, y eso es una tanda de patrones.
 * ⚠️ Mientras tanto: si cambia la altura del `size="sm"` del select, cambia también acá. Son dos
 * lugares con un solo valor, y el que se olvide vuelve a partir la barra.
 */
const FIELD_CLASS =
  "h-11 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground md:h-[30px] " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 " +
  // Mismo tratamiento de deshabilitado que `select.tsx`: durante la carga los filtros quedan a la
  // vista pero no se pueden tocar, y tienen que LEERSE como no tocables, no solo ignorar el click.
  "disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50"

/**
 * Agrega o saca un valor de la selección. Devuelve un array nuevo (no muta).
 * Exportada para poder testear la propagación del multiselect sin un DOM: es la única
 * lógica no trivial del componente.
 */
export function alternar(seleccion: string[], value: string): string[] {
  return seleccion.includes(value) ? seleccion.filter((v) => v !== value) : [...seleccion, value]
}

export function Campo({ campo, disabled }: { campo: FiltroCampo; disabled?: boolean }) {
  switch (campo.tipo) {
    case "select":
      return (
        <Select size="sm" className="w-auto" disabled={disabled} value={campo.value} onChange={(e) => campo.onChange(e.target.value)}>
          <option value="">{campo.opcionTodos ?? "Todos"}</option>
          {campo.opciones.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </Select>
      )
    case "date":
      return (
        <input type="date" className={FIELD_CLASS} disabled={disabled} value={campo.value} onChange={(e) => campo.onChange(e.target.value)} />
      )
    case "daterange":
      return (
        <div className="flex items-center gap-2">
          <input
            type="date" className={FIELD_CLASS} disabled={disabled} value={campo.value.desde} aria-label={`${campo.label} — desde`}
            onChange={(e) => campo.onChange({ ...campo.value, desde: e.target.value })}
          />
          <span aria-hidden="true" className="text-muted-foreground">–</span>
          <input
            type="date" className={FIELD_CLASS} disabled={disabled} value={campo.value.hasta} aria-label={`${campo.label} — hasta`}
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
                type="checkbox" className="size-4 rounded border-input" disabled={disabled}
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
          type="search" className={FIELD_CLASS} disabled={disabled} value={campo.value}
          placeholder={campo.placeholder} onChange={(e) => campo.onChange(e.target.value)}
        />
      )
  }
}
