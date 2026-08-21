import { UserSearch } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { textoVacio } from "@/components/ui/textoVacio"
import type { CandidatoConGrupo, GrupoCandidatos } from "@/types/candidato"

import { CandidatoGrupo } from "./CandidatoGrupo"

/**
 * La lista agrupada de candidatos con sus tres estados: carga, error y vacío.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 EL VACÍO ACÁ NO ES `TablaVacia`, Y NO PUEDE SERLO.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * `TablaVacia` renderiza un `<TableBody>` con una fila de `colSpan`, que es exactamente lo que
 * conserva el encabezado y los anchos de las columnas. Acá no hay tabla: son TARJETAS por
 * búsqueda, con las filas adentro. Lo que sí se conserva es la parte que importa: el TEXTO sale
 * de `textoVacio()`, el mismo helper y con los mismos chips, así que la frase se arma con los
 * valores reales de los filtros igual que en las pantallas de tabla. Mismo precedente que
 * `PerfilesGrid`.
 *
 * ⚠️ SIN SUJETO (`claveSujeto`), y no es un olvido: el sujeto de esa frase es siempre la EMPRESA
 * ("Karstec no tiene…"), y acá la empresa NO es un filtro de la pantalla — llega por el selector
 * del sidebar, en el header del request. Ninguno de los dos filtros es nominal, así que la frase
 * arranca impersonal: "No hay candidatos con clasificación Relevante".
 */
export function CandidatosLista({
  grupos, loading, error, chips, onRetry, onSelect, onLimpiarTodo,
}: {
  grupos: GrupoCandidatos[]
  loading: boolean
  error: boolean
  chips: ChipFiltro[]
  onRetry: () => void
  onSelect: (c: CandidatoConGrupo) => void
  onLimpiarTodo: () => void
}) {
  if (error) return <ErrorState action={onRetry} />

  if (loading) {
    // El esqueleto son TARJETAS del mismo alto que las reales, no barras: así la pantalla no
    // cambia de forma cuando llegan los datos. Mismo criterio que el esqueleto de las tablas.
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => <Skeleton key={i} shimmer className="h-40 w-full rounded-xl" />)}
      </div>
    )
  }

  if (grupos.length === 0) {
    const { titulo, descripcion } = textoVacio(chips, "candidatos")
    const ultimo = chips[chips.length - 1]
    return (
      <EmptyState
        icon={<UserSearch />}
        title={titulo}
        description={descripcion}
        /* Las dos salidas del patrón: quitar el último filtro (el que el usuario acaba de poner)
           o limpiar todo. Nunca se ejecutan solas: si la pantalla se limpiara sola, el usuario
           vería aparecer filas sin entender que las está mirando sin el filtro que puso.
           Sin filtros no hay nada que quitar, y tampoco hay un alta que ofrecer: los candidatos
           entran por el formulario público o por la casilla, no desde esta pantalla. */
        action={ultimo ? (
          <div className="flex flex-wrap items-center justify-center gap-2">
            <Button variant="outline" className="min-h-11" onClick={ultimo.quitar}>
              Quitar {ultimo.etiqueta.toLowerCase()}: {ultimo.valor}
            </Button>
            <Button variant="ghost" className="min-h-11" onClick={onLimpiarTodo}>Limpiar todo</Button>
          </div>
        ) : undefined}
      />
    )
  }

  return (
    <>
      {grupos.map((grupo) => (
        <CandidatoGrupo key={grupo.nombre} grupo={grupo} onSelect={onSelect} />
      ))}
    </>
  )
}
