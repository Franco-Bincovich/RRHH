import { Skeleton } from "@/components/ui/skeleton"
import { Campo, Panel } from "@/components/ui/fichaPanel"

/**
 * Los primitivos de la ficha de un legajo.
 *
 * 🔴 `Field` Y `Section` YA NO SE DEFINEN ACÁ: son `Campo` y `Panel` de
 * `components/ui/fichaPanel.tsx`, compartidos con las otras cinco fichas. Se re-exportan con los
 * nombres viejos por una razón concreta y no por comodidad: los importan **nueve archivos**, y
 * renombrarlos en la misma tanda que agrega cinco fichas mezcla dos cambios que se revisan
 * distinto. El nombre canónico es el de `fichaPanel`; el día que se toque uno de esos nueve, se
 * cambia el import y esta línea se achica sola.
 *
 * Lo único propio que queda es el esqueleto, que sí es de esta ficha: describe SU grilla.
 */
export { Campo as Field, Panel as Section }

/**
 * Placeholder de carga de la ficha de un legajo: la barra de identidad y las tres columnas de
 * paneles, con la misma forma que van a tener con datos (§3, "esqueleto con la grilla exacta").
 * El shimmer de 1,2s es el del sistema de diseño, no el `animate-pulse` de 2s del componente.
 */
export function LoadingSkeleton() {
  return (
    <div>
      <Skeleton shimmer className="mb-4 h-[118px] w-full rounded-xl" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Skeleton shimmer className="h-64 w-full rounded-xl" />
        <Skeleton shimmer className="h-64 w-full rounded-xl" />
        <Skeleton shimmer className="h-40 w-full rounded-xl" />
      </div>
    </div>
  )
}
