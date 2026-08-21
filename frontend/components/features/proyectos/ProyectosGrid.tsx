"use client"

/**
 * Grilla de proyectos: presentacional. Cubre los cuatro estados del listado (cargando / error /
 * vacío / datos) y no sabe nada de filtros ni de fetch.
 *
 * Se llama Grid y no Table porque eso es lo que renderiza: tarjetas, no una tabla. UNA tarjeta
 * vive en `ProyectoCard.tsx` — se mudó ahí al sumarle el patrón del bloque B, que llevaba este
 * archivo a 180 líneas contra un límite de 150.
 */
import { FolderKanban } from "lucide-react"
import type { ReactNode } from "react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { GrillaTarjetas } from "@/components/ui/GrillaTarjetas"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { textoVacio } from "@/components/ui/textoVacio"
import type { Proyecto } from "@/types/proyecto"

import { ProyectoCard } from "./ProyectoCard"

interface ProyectosGridProps {
  proyectos: Proyecto[]
  loading: boolean
  error: string | null
  canWrite: boolean
  onEdit: (p: Proyecto) => void
  onRetry: () => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` sin permiso. */
  accionVacio?: ReactNode
}

/**
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 EL VACÍO ACÁ NO ES `TablaVacia`, Y NO PUEDE SERLO.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * `TablaVacia` renderiza un `<TableBody>` con una fila de `colSpan`, que es exactamente lo que
 * conserva el encabezado y los anchos de las columnas. Acá no hay tabla: son TARJETAS (§5, "cosas
 * que se eligen, no registros que se comparan"), sin encabezado que conservar ni `colSpan` que
 * contar. Lo que sí se conserva es la parte que importa: el TEXTO sale de `textoVacio()`, el mismo
 * helper y con los mismos chips, así que la frase se arma con los valores reales de los filtros
 * igual que en las pantallas de tabla. Mismo precedente que `PerfilesGrid` y `CandidatosLista`.
 *
 * 🔴 Y ESE TEXTO ES EL ARREGLO, no un cambio de estilo: hasta ahora el vacío decía "No hay
 * proyectos registrados" **con tres filtros puestos**. Es verdadero, no dice cuál de los tres
 * dejó la pantalla en cero, y sobre un padrón con proyectos cargados es directamente engañoso.
 */
export function ProyectosGrid({
  proyectos, loading, error, canWrite, onEdit, onRetry, chips, onLimpiarTodo, accionVacio,
}: ProyectosGridProps) {
  if (loading) {
    // El esqueleto son TARJETAS del mismo alto que las reales, con el shimmer de 1,2s que pide
    // §3 (y no el `animate-pulse` de 2s): así la pantalla no cambia de forma al llegar los datos.
    return (
      <GrillaTarjetas>
        {[1, 2, 3].map((i) => <Skeleton key={i} shimmer className="h-60 rounded-xl" />)}
      </GrillaTarjetas>
    )
  }
  if (error) return <ErrorState description={error} action={onRetry} />
  if (proyectos.length === 0) {
    const { titulo, descripcion } = textoVacio(chips, "proyectos", "Empresa")
    const ultimo = chips[chips.length - 1]
    return (
      <EmptyState
        icon={<FolderKanban />}
        title={titulo}
        description={descripcion}
        /* Las dos salidas del patrón: quitar el último filtro (el que el usuario acaba de poner)
           o limpiar todo. Nunca se ejecutan solas: si la pantalla se limpiara sola, el usuario
           vería aparecer tarjetas sin entender que las está mirando sin el filtro que puso. */
        action={ultimo ? (
          <div className="flex flex-wrap items-center justify-center gap-2">
            <Button variant="outline" className="min-h-11" onClick={ultimo.quitar}>
              Quitar {ultimo.etiqueta.toLowerCase()}: {ultimo.valor}
            </Button>
            <Button variant="ghost" className="min-h-11" onClick={onLimpiarTodo}>Limpiar todo</Button>
          </div>
        ) : accionVacio}
      />
    )
  }
  return (
    <GrillaTarjetas>
      {proyectos.map((p) => (
        <ProyectoCard key={p.id} proyecto={p} canWrite={canWrite} onEdit={onEdit} />
      ))}
    </GrillaTarjetas>
  )
}
