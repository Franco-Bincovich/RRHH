"use client"

import { ArrowRight, CheckSquare, ChevronRight, Plus, TrendingUp } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { readinessBarColor } from "./_sucesion_ui"
import type { PlanCarrera } from "@/types/sucesion"

// El esqueleto conserva las tres líneas de la fila real —nombre, trayecto y barra de readiness—
// para que al llegar los datos nada se mueva de lugar. `shimmer` en vez del `animate-pulse` de 2s,
// que late más lento que el resto del sistema.
function PlanesSkeleton() {
  return (
    <ul className="divide-y divide-border">
      {Array.from({ length: 3 }).map((_, i) => (
        <li key={i} className="py-4 space-y-2">
          <Skeleton shimmer className="h-4 w-40" />
          <Skeleton shimmer className="h-3 w-56" />
          <Skeleton shimmer className="h-1.5 w-full rounded-full" />
        </li>
      ))}
    </ul>
  )
}

export function PlanesTab({
  planes, loading, error, onReintentar, mostrarEmpresa, canWrite, onNuevoPlan, onVerDetalle,
}: {
  planes: PlanCarrera[]
  loading: boolean
  error: string | null
  onReintentar: () => void
  mostrarEmpresa: boolean
  canWrite: boolean
  onNuevoPlan: () => void
  onVerDetalle: (plan: PlanCarrera) => void
}) {
  return (
    <Card as="section" aria-label="Planes de carrera activos">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">Planes activos</h2>
        <div className="flex items-center gap-3">
          {!loading && !error && planes.length > 0 && (
            <span className="text-sm text-muted-foreground">{planes.length} colaboradores</span>
          )}
          {canWrite && (
            <Button size="sm" onClick={onNuevoPlan} className="min-h-9 gap-1.5">
              <Plus className="size-3.5" />
              Nuevo plan
            </Button>
          )}
        </div>
      </div>

      {loading && <PlanesSkeleton />}
      {/* 🔴 EL ERROR ES `ErrorState`, NO UN `EmptyState` CON TÍTULO DE ERROR. No es lo mismo "no
          hay planes" que "no sabemos si hay planes": el primero es un dato, el segundo es una
          falla, y hasta esta tanda las dos se dibujaban con el mismo cartel gris y sin salida.
          `ErrorState` trae el reintento, que es lo único accionable de los dos casos. */}
      {!loading && error && (
        <ErrorState title="No se pudieron cargar los planes" description={error} action={onReintentar} />
      )}
      {!loading && !error && planes.length === 0 && (
        <EmptyState
          icon={<TrendingUp />}
          title="Todavía no hay planes de carrera"
          /* Copy propio en vez del genérico de `textoVacio`: esta lista no tiene filtros, así que
             la rama genérica sólo podría decir "cuando se cargue el primero va a aparecer acá" y
             ahí se pierde lo único que importa —qué es un plan y para qué sirve tener uno—. Para
             `gerencia_lectura`, que no puede crearlos, la frase sigue siendo cierta y no le pide
             nada; el botón de alta ya está arriba y sólo con permiso. */
          description="Un plan de carrera es el trayecto de una persona de su cargo actual a uno objetivo, con hitos y un porcentaje de readiness. Sin ninguno cargado, el seguimiento de desarrollo vive fuera del sistema."
        />
      )}
      {!loading && !error && planes.length > 0 && (
        <ul className="divide-y divide-border" role="list">
          {planes.map((plan) => (
            <li key={plan.id} className="py-4 first:pt-0 last:pb-0">
              <div className="flex flex-col gap-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold text-foreground">{plan.empleado_nombre}</p>
                    {mostrarEmpresa && plan.empresa_nombre && (
                      <p className="text-xs text-muted-foreground">{plan.empresa_nombre}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <CheckSquare className="size-3.5" />
                      <span>{plan.hitos_completados}/{plan.hitos_total} hitos</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onVerDetalle(plan)}
                      className="min-h-8 gap-1 text-xs"
                    >
                      Ver detalle
                      <ChevronRight className="size-3" />
                    </Button>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-sm">
                  <span className="text-muted-foreground">{plan.cargo_actual ?? "—"}</span>
                  <ArrowRight className="size-3.5 shrink-0 text-muted-foreground" />
                  <span className="font-medium text-foreground">{plan.cargo_objetivo}</span>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Readiness</span>
                    <span className="font-medium text-foreground">{plan.readiness}%</span>
                  </div>
                  <div
                    className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
                    role="progressbar"
                    aria-valuenow={plan.readiness}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`Readiness de ${plan.empleado_nombre}`}
                  >
                    <div
                      className={`h-full rounded-full transition-all ${readinessBarColor(plan.readiness)}`}
                      style={{ width: `${plan.readiness}%` }}
                    />
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
