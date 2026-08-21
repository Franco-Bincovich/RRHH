import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

/**
 * La grilla de las pantallas que son TARJETAS y no listas (`docs/SISTEMA-DE-DISENO.md` §5:
 * perfiles de puesto, reportes, comunicación — "cosas que se eligen, no registros que se
 * comparan").
 *
 * 🔴 POR QUÉ EXISTE, medido antes de escribirlo: el literal
 * `grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3` estaba **copiado 4 veces en 3 archivos**
 * (`ReportesCatalogo`, `ProyectosGrid` ×2 — la grilla real y su esqueleto — y `CardsProyecto`), y
 * perfiles de puesto iba a ser la quinta. Las cuatro eran todavía IDÉNTICAS, y ese es justamente
 * el momento de extraer: el precedente de `components/ui/select.tsx` es el mismo tratamiento
 * copiado a mano que para cuando alguien lo miró ya tenía **10 valores distintos** repartidos en
 * 14 archivos, y ahí unificar dejó de ser cambiar una clase y pasó a ser rehacer pantallas.
 *
 * ⚠️ NO ES UN COMPONENTE DE TARJETA: es la grilla que las acomoda. La tarjeta en sí la pone cada
 * módulo, porque lo que muestra cada una es distinto (`ReporteCard` trae selectores y un botón,
 * `PerfilCard` cuatro campos y dos acciones). Lo único compartido es el reparto en columnas y el
 * aire entre ellas — y eso es lo que §5 fija.
 *
 * ⚠️ POR QUÉ LOS BREAKPOINTS SON ESOS Y NO OTROS: 1 columna en mobile, 2 desde `sm`, 3 desde
 * `xl` — y NO desde `lg`. Con el sidebar abierto, `lg` deja tres tarjetas de ~230px y el resumen
 * del perfil (o la descripción del reporte) se corta en dos palabras por línea. Es el reparto que
 * las cuatro copias ya usaban; se conserva tal cual, no se "mejora" en la extracción.
 */
export function GrillaTarjetas({
  children, className,
}: {
  children: ReactNode
  /** Para el esqueleto de carga (`animate-pulse`) y poco más. No para cambiar las columnas. */
  className?: string
}) {
  return (
    <div className={cn("grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3", className)}>
      {children}
    </div>
  )
}
