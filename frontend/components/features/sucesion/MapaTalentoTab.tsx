"use client"

import { Filter, Layers, Search } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { Button } from "@/components/ui/button"
import { NineBox } from "./NineBox"
import type { EmpleadoCelda } from "./NineBox"
import { SELECT_CLASS, toEmpleadoCelda } from "./_sucesion_ui"
import type { Area } from "@/types/area"
import type { EmpleadoMapa } from "@/types/sucesion"

function MapaSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-6 w-32 rounded bg-muted" />
      <div className="grid grid-cols-3 gap-1">
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="min-h-[100px] rounded-lg bg-muted" />
        ))}
      </div>
    </div>
  )
}

export function MapaTalentoTab({
  empleados, areas, selectedArea, onSelectArea, loading, error, onAnalizar,
}: {
  empleados: EmpleadoMapa[]
  areas: Area[]
  selectedArea: string
  onSelectArea: (areaId: string) => void
  loading: boolean
  error: string | null
  onAnalizar: () => void
}) {
  const empleadosFiltrados: EmpleadoCelda[] = (
    selectedArea
      ? empleados.filter((e) => e.area_id === selectedArea)
      : empleados
  ).map(toEmpleadoCelda)

  return (
    <>
      <section className="rounded-xl border bg-card p-4 md:p-6" aria-label="Mapa 9-box de talento">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-foreground">Mapa 9-Box</h2>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5">
              <Filter className="size-3.5 text-muted-foreground" />
              <select
                value={selectedArea}
                onChange={(e) => onSelectArea(e.target.value)}
                className={SELECT_CLASS}
                aria-label="Filtrar por área"
              >
                <option value="">Todas las áreas</option>
                {areas.map((a) => (
                  <option key={a.id} value={a.id}>{a.nombre}</option>
                ))}
              </select>
            </div>
            <p className="hidden text-xs text-muted-foreground md:block">
              Clic en un empleado para ver detalle
            </p>
          </div>
        </div>

        {loading && <MapaSkeleton />}
        {!loading && error && (
          <EmptyState icon={<Layers />} title="Error al cargar el mapa" description={error} />
        )}
        {!loading && !error && empleadosFiltrados.length === 0 && (
          <EmptyState
            icon={<Layers />}
            title="Sin empleados en el mapa"
            description={selectedArea
              ? "No hay empleados en esta área con potencial y desempeño asignados."
              : "Asigná potencial y desempeño a los empleados activos para verlos aquí."}
          />
        )}
        {!loading && !error && empleadosFiltrados.length > 0 && (
          <NineBox empleados={empleadosFiltrados} />
        )}
      </section>

      <section className="rounded-xl border bg-card p-4 md:p-6">
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
      </section>
    </>
  )
}
