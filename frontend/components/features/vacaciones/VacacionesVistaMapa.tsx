import { Umbrella } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { textoVacio } from "@/components/ui/textoVacio"
import type { SolicitudVacaciones } from "@/types/vacaciones"

import { MapaVacaciones } from "./MapaVacaciones"

/**
 * La vista "mapa" de /vacaciones con sus tres estados: carga, error y vacío.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 EL VACÍO ACÁ NO ES `TablaVacia`, Y NO PUEDE SERLO.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * `TablaVacia` renderiza un `<TableBody>` con una fila de `colSpan`, que es exactamente lo que
 * conserva el encabezado y los anchos de las columnas. El mapa es un calendario: no tiene
 * encabezado de columnas que conservar ni `colSpan` que contar. Lo que sí se conserva es la parte
 * que importa: el TEXTO sale de `textoVacio()`, el MISMO helper y con los MISMOS chips que la
 * vista lista, así que la frase se arma con los valores reales de los filtros en las dos.
 * Mismo precedente que `PerfilesGrid`, que es de tarjetas y hace lo mismo.
 *
 * Existe como componente aparte —y no adentro de la página— porque la página quedaba dueña de
 * dos juegos de estados a la vez, uno por vista, y ese reparto es justo lo que hacía que el
 * vacío de la lista no pudiera vivir adentro de la `<Table>`.
 */
export function VacacionesVistaMapa({
  items, loading, error, onRetry, chips,
}: {
  items: SolicitudVacaciones[]
  loading: boolean
  error: boolean
  onRetry: () => void
  chips: ChipFiltro[]
}) {
  if (error) return <ErrorState action={onRetry} />

  // El esqueleto es del alto del calendario, no una pila de barras de fila: así la pantalla no
  // cambia de forma cuando llegan los datos. Mismo criterio que el esqueleto de las tablas.
  if (loading) return <Skeleton shimmer className="h-80 w-full rounded-lg" />

  if (items.length === 0) {
    const { titulo, descripcion } = textoVacio(chips, "vacaciones", "Empresa", "femenino")
    return <EmptyState icon={<Umbrella />} title={titulo} description={descripcion} />
  }

  return <MapaVacaciones solicitudes={items} />
}
