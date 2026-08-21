import { ArrowRight } from "lucide-react"

import type { ParCambio } from "./_cambios"

/**
 * Los pares "de → a" de una recategorización, con **la flecha en acento** — el mismo tratamiento
 * que el historial del patrón de ficha (`docs/SISTEMA-DE-DISENO.md` §3), para que un cambio se
 * lea igual en las dos superficies del producto.
 *
 * 🔴 SOLO LOS PARES QUE CAMBIARON. La lista ya viene filtrada por `paresCambiados`, y la decisión
 * está explicada ahí: dibujar los tres campos siempre llenaría dos tercios de la celda con
 * "— → —" para la mayoría de las filas, que es ruido con forma de dato.
 *
 * 🔴 SIN VALOR PREVIO NO HAY FLECHA. Un par cuyo `desde` es `null` es el primer valor que esa
 * persona tuvo en ese campo, y se muestra solo. Poner "— →" ahí se lee como si antes hubiera
 * habido algo que se borró.
 *
 * El label de cada par ("Rol", "Seniority", "Categoría") va adelante y en chico: con hasta tres
 * pares apilados, sin él no se sabe cuál es cuál — dos de los tres son texto libre y pueden
 * parecerse entre sí.
 */
export function CeldaCambios({ pares }: { pares: ParCambio[] }) {
  return (
    <div className="flex flex-col gap-0.5">
      {pares.map((p) => (
        <span key={p.clave} className="flex flex-wrap items-baseline gap-1.5">
          <span className="w-16 shrink-0 text-xs text-muted-foreground">{p.label}</span>
          {p.desde && (
            <>
              <span className="text-sm text-muted-foreground line-through">{p.desde}</span>
              <ArrowRight className="size-3.5 shrink-0 text-accent-foreground" aria-label="cambia a" />
            </>
          )}
          <span className="text-sm font-medium text-foreground">{p.hasta}</span>
        </span>
      ))}
    </div>
  )
}
