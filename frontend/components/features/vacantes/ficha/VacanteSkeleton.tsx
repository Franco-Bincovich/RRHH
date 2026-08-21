import { Skeleton } from "@/components/ui/skeleton"

/**
 * El placeholder de carga de la ficha de una vacante: la barra de identidad, un panel y las cinco
 * columnas del tablero, con la GRILLA EXACTA que van a tener con datos (§3).
 *
 * Vive aparte y no adentro de la página por el límite de líneas: `[id]/page.tsx` venía de 452
 * contra un tope de 150 y quedó a un renglón de volver a tocarlo. Sacar el esqueleto es el corte
 * más barato que le da aire, porque no comparte nada con el resto de la página.
 */
export function VacanteSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton shimmer className="h-[118px] w-full rounded-xl" />
      <Skeleton shimmer className="h-40 w-full rounded-xl" />
      <div className="flex gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} shimmer className="h-48 w-72 flex-shrink-0 rounded-xl" />
        ))}
      </div>
    </div>
  )
}
