"use client"

import { ArrowRight, CheckSquare, ChevronRight, Plus, TrendingUp } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { readinessBarColor } from "./_sucesion_ui"
import type { PlanCarrera } from "@/types/sucesion"

function PlanesSkeleton() {
  return (
    <ul className="divide-y divide-border">
      {Array.from({ length: 3 }).map((_, i) => (
        <li key={i} className="animate-pulse py-4 space-y-2">
          <div className="h-4 w-40 rounded bg-muted" />
          <div className="h-3 w-56 rounded bg-muted" />
          <div className="h-1.5 w-full rounded-full bg-muted" />
        </li>
      ))}
    </ul>
  )
}

export function PlanesTab({
  planes, loading, error, mostrarEmpresa, canWrite, onNuevoPlan, onVerDetalle,
}: {
  planes: PlanCarrera[]
  loading: boolean
  error: string | null
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
      {!loading && error && (
        <EmptyState icon={<TrendingUp />} title="Error al cargar los planes" description={error} />
      )}
      {!loading && !error && planes.length === 0 && (
        <EmptyState
          icon={<TrendingUp />}
          title="Sin planes de carrera"
          description="Todavía no hay planes de carrera activos registrados."
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
