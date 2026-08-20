import { cn } from "@/lib/utils"

/**
 * El brillo que recorre la barra: `docs/SISTEMA-DE-DISENO.md` §3 pide **shimmer de 1,2s** para el
 * esqueleto de una tabla, y el default de este componente es un `animate-pulse` de 2s, que es un
 * fundido de opacidad sin dirección. La animación está declarada en `app/globals.css`.
 *
 * `bg-[length:200%_100%]` es lo que le da recorrido al gradiente: sin eso el `background-position`
 * anima sobre un fondo del tamaño exacto de la barra y no se mueve nada.
 */
const SHIMMER =
  "animate-shimmer bg-[linear-gradient(90deg,var(--muted)_0%,var(--border)_50%,var(--muted)_100%)] bg-[length:200%_100%]"

function Skeleton({ className, shimmer, ...props }: React.ComponentProps<"div"> & {
  /** Opt-in: el resto de los ~30 consumidores sigue con el `animate-pulse` de siempre. */
  shimmer?: boolean
}) {
  return (
    <div
      data-slot="skeleton"
      className={cn("animate-pulse rounded-md bg-muted", shimmer && SHIMMER, className)}
      {...props}
    />
  )
}

export { Skeleton }
