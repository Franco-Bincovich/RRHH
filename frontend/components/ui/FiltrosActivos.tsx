import { X } from "lucide-react"

import type { ChipFiltro } from "@/components/ui/filtrosChips"

/**
 * La FILA INFERIOR del panel de filtros (`docs/SISTEMA-DE-DISENO.md` §3): contador
 * ("2 filtros activos"), un chip por filtro con su valor y una ✕ para quitarlo, y "Limpiar todo".
 *
 * 🔴 SOLO APARECE SI HAY FILTROS ACTIVOS. Sin ninguno devuelve `null` — no una fila vacía ni un
 * contenedor de alto cero: el panel tiene que verse igual que antes del patrón cuando no hay nada
 * filtrado, y una fila fantasma corre la tabla dos píxeles cada vez que se pone o se saca un chip.
 *
 * 🔴 ES EL ÚNICO RELLENO AZUL DE LA PANTALLA. Los chips usan `--accent` con borde `--primary`
 * (§3). Si aparece otro relleno azul en el listado, o es un botón primario que no debería ser
 * primario, o alguien copió estas clases para otra cosa.
 *
 * Presentacional puro: no conoce filtros ni pantallas, solo la lista de chips ya derivada por
 * `filtrosChips.ts`. "Limpiar todo" es cada chip quitándose a sí mismo, así que hereda el mismo
 * camino —y el mismo reseteo a página 1— que quitar uno a mano.
 */
export function FiltrosActivos({ chips, disabled }: { chips: ChipFiltro[]; disabled?: boolean }) {
  if (chips.length === 0) return null

  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
      <span className="text-xs text-muted-foreground tabular-nums">
        {chips.length === 1 ? "1 filtro activo" : `${chips.length} filtros activos`}
      </span>

      {chips.map((chip) => (
        <span
          key={chip.clave}
          className="inline-flex items-center gap-1 rounded-md border border-primary bg-accent py-0.5 pl-2 pr-0.5 text-xs text-accent-foreground"
        >
          {/* El nombre del filtro en peso normal y el valor en semibold: con muchos chips puestos
              lo que se busca de un vistazo es el VALOR, no la etiqueta que se repite en todos. */}
          <span>{chip.etiqueta}:</span>
          <span className="font-semibold">{chip.valor}</span>
          <button
            type="button"
            onClick={chip.quitar}
            disabled={disabled}
            /* ⚠️ El área tocable de la ✕ es de 32px en mobile, no de los 44px que el repo usa para
               los controles de formulario. Un chip de 44px de alto sería más alto que el buscador
               que tiene arriba y la fila dejaría de leerse como un resumen. El filtro igual se
               puede quitar desde su propio control, que sí tiene 44px. */
            className="flex size-8 items-center justify-center rounded-sm text-accent-foreground/70 transition-colors hover:bg-primary hover:text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 md:size-5"
            aria-label={`Quitar filtro ${chip.etiqueta}`}
          >
            <X className="size-3" aria-hidden="true" />
          </button>
        </span>
      ))}

      <button
        type="button"
        onClick={() => chips.forEach((c) => c.quitar())}
        disabled={disabled}
        className="ml-auto rounded-md px-2 py-1 text-xs text-muted-foreground underline-offset-2 transition-colors hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50"
      >
        Limpiar todo
      </button>
    </div>
  )
}
