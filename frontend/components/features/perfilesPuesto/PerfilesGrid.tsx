import { IdCard } from "lucide-react"
import type { ReactNode } from "react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { GrillaTarjetas } from "@/components/ui/GrillaTarjetas"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { textoVacio } from "@/components/ui/textoVacio"
import type { CamposPerfilResponse, PerfilPuesto } from "@/types/perfilPuesto"

import { PerfilCard } from "./PerfilCard"

/**
 * La grilla de perfiles con sus tres estados: carga, error y vacío.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 EL VACÍO ACÁ NO ES `TablaVacia`, Y NO SE PUEDE SERLO.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * El patrón de vacío del bloque B está escrito para TABLA: `TablaVacia` renderiza un
 * `<TableBody>` con una fila de `colSpan`, que es lo que conserva el encabezado y los anchos de
 * las columnas. Acá no hay tabla, ni encabezado que conservar, ni columnas que contar — §5 dice
 * que perfiles es una pantalla de TARJETAS. Lo que sí se conserva es la parte que importa: el
 * TEXTO sale de `textoVacio()`, el mismo helper y con los mismos chips, así que la frase se arma
 * con los valores reales de los filtros igual que en las pantallas de tabla.
 *
 * ⚠️ SIN SUJETO (`claveSujeto`), y no es un olvido: el sujeto de esa frase es siempre la EMPRESA
 * ("Bodegas Tupungato no tiene…"), y acá no hay empresa — el catálogo es del grupo. Ninguno de
 * los dos filtros es nominal, así que sin filtros la frase cae a la rama "Todavía no hay perfiles
 * de puesto", que con 0 filas en producción es exactamente la correcta.
 */
export function PerfilesGrid({
  perfiles, catalogos, loading, error, canWrite, chips, onRetry, onEdit, onBaja, onReactivar,
  accionVacio,
}: {
  perfiles: PerfilPuesto[]
  catalogos: CamposPerfilResponse | null
  loading: boolean
  error: string | null
  canWrite: boolean
  chips: ChipFiltro[]
  onRetry: () => void
  onEdit: (p: PerfilPuesto) => void
  onBaja: (p: PerfilPuesto) => void
  onReactivar: (p: PerfilPuesto) => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` si no puede escribir. */
  accionVacio?: ReactNode
}) {
  if (error) return <ErrorState description={error} action={onRetry} />

  if (loading) {
    // El esqueleto son TARJETAS del mismo alto, no barras: así la pantalla no cambia de forma
    // cuando llegan los datos. Mismo criterio que el esqueleto de las tablas.
    return (
      <GrillaTarjetas className="animate-pulse">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Card key={i} padding="sm" className="h-44 bg-muted" />
        ))}
      </GrillaTarjetas>
    )
  }

  if (perfiles.length === 0) {
    const { titulo, descripcion } = textoVacio(chips, "perfiles de puesto")
    const ultimo = chips[chips.length - 1]
    return (
      <EmptyState
        icon={<IdCard />}
        title={titulo}
        description={descripcion}
        // Las dos salidas del patrón: quitar el último filtro (el que el usuario acaba de poner)
        // o, si no hay ninguno, crear el primero. Nunca se ejecutan solas.
        action={ultimo ? (
          <Button variant="outline" className="min-h-11" onClick={ultimo.quitar}>
            Quitar {ultimo.etiqueta.toLowerCase()}: {ultimo.valor}
          </Button>
        ) : accionVacio}
      />
    )
  }

  return (
    <GrillaTarjetas>
      {perfiles.map((p) => (
        <PerfilCard
          key={p.id}
          perfil={p}
          catalogos={catalogos}
          canWrite={canWrite}
          onEdit={onEdit}
          onBaja={onBaja}
          onReactivar={onReactivar}
        />
      ))}
    </GrillaTarjetas>
  )
}
