"use client"

import { Layers, Search } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { NineBox, type EmpleadoCelda } from "./NineBox"
import { construirCamposSucesion } from "./_camposSucesion"
import { toEmpleadoCelda } from "./_sucesion_ui"
import type { Area } from "@/types/area"
import type { EmpleadoMapa } from "@/types/sucesion"

/**
 * El esqueleto dibuja la MISMA grilla de 3×3 que va a aparecer, con el mismo alto de celda: es la
 * regla del patrón (§3) —el esqueleto tiene la forma de lo que llega— y acá evita el salto de
 * layout más grande de la pantalla.
 *
 * `shimmer` y no `animate-pulse`: el pulse de 2s late más lento que el resto del sistema y en una
 * grilla de nueve bloques grandes se nota como un parpadeo.
 */
function MapaSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton shimmer className="h-6 w-32" />
      <div className="grid grid-cols-3 gap-1">
        {Array.from({ length: 9 }).map((_, i) => (
          <Skeleton key={i} shimmer className="min-h-[100px] rounded-lg" />
        ))}
      </div>
    </div>
  )
}

export function MapaTalentoTab({
  empleados, areas, selectedArea, onSelectArea, loading, error, onReintentar, onAnalizar,
}: {
  empleados: EmpleadoMapa[]
  areas: Area[]
  selectedArea: string
  onSelectArea: (areaId: string) => void
  loading: boolean
  error: string | null
  onReintentar: () => void
  onAnalizar: () => void
}) {
  const campos = construirCamposSucesion({ areas, area: selectedArea, setArea: onSelectArea })
  const chips = chipsDeCampos(campos)

  const empleadosFiltrados: EmpleadoCelda[] = (
    selectedArea
      ? empleados.filter((e) => e.area_id === selectedArea)
      : empleados
  ).map(toEmpleadoCelda)

  return (
    <>
      <Card as="section" aria-label="Mapa 9-box de talento">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-foreground">Mapa 9-Box</h2>
          <p className="hidden text-xs text-muted-foreground md:block">
            Clic en un empleado para ver detalle
          </p>
        </div>

        {/* `panel`: la forma completa del patrón —caja propia y la fila de chips abajo—. Un solo
            campo, así que no hay nada detrás de "Más filtros". `disabled` durante la carga: el
            filtro queda A LA VISTA con su chip pero no se puede tocar (§3). */}
        <FiltersBar campos={campos} panel disabled={loading} />

        {loading && <MapaSkeleton />}
        {!loading && error && (
          <ErrorState title="No se pudo cargar el mapa de talento" description={error} action={onReintentar} />
        )}
        {!loading && !error && empleadosFiltrados.length === 0 && (
          <EmptyState
            icon={<Layers />}
            title="Sin colaboradores en el mapa"
            /* 🔴 EL VACÍO NOMBRA EL ÁREA REAL, no "esta área". El valor sale del chip, o sea de la
               misma opción que llena el selector: no puede decir un uuid ni un nombre viejo.
               Y dice lo que la ausencia SIGNIFICA: el 9-box necesita potencial Y desempeño
               cargados, así que un padrón entero sin esos dos campos deja el mapa vacío sin que
               falte nadie. */
            description={chips.length > 0
              ? `Nadie de ${chips[0].valor} tiene potencial y desempeño cargados.`
              : "El mapa cruza potencial con desempeño: hasta que esos dos campos no estén cargados en las fichas, no hay a quién ubicar."}
          />
        )}
        {!loading && !error && empleadosFiltrados.length > 0 && (
          <NineBox empleados={empleadosFiltrados} />
        )}
      </Card>

      <Card as="section">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-foreground">Análisis por área</h2>
            <p className="mt-0.5 text-sm text-muted-foreground">
              Rankeá a los empleados activos de un área por su score de assessment.
            </p>
          </div>
          <Button onClick={onAnalizar} className="min-h-11 shrink-0 gap-2">
            <Search className="size-4" />
            Analizar área
          </Button>
        </div>
      </Card>
    </>
  )
}
