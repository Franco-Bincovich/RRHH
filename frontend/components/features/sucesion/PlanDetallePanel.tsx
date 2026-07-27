"use client"

import { useState } from "react"
import { ArrowRight, Plus, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { HitosList } from "./HitosList"
import { NuevoHitoForm } from "./NuevoHitoForm"
import type { PlanDetalle } from "./usePlanDetalle"
import type { PlanCarrera } from "@/types/sucesion"

export function PlanDetallePanel({
  plan, detalle, canWrite,
}: {
  plan: PlanCarrera
  detalle: PlanDetalle
  canWrite: boolean
}) {
  const {
    cerrar, hitos, hitosLoading, hitosError, completar, agregarHito,
    readinessEdit, setReadinessEdit, readinessSaving, guardarReadiness,
  } = detalle
  const [nuevoHitoOpen, setNuevoHitoOpen] = useState(false)

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
        onClick={cerrar}
        aria-hidden
      />
      <div
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-background shadow-2xl border-l"
        role="dialog"
        aria-label={`Detalle del plan de ${plan.empleado_nombre}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-base font-semibold text-foreground">Plan de carrera</h2>
          <Button variant="ghost" size="icon" className="size-9" onClick={cerrar}>
            <X className="size-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Employee info */}
          <div>
            <p className="text-lg font-semibold text-foreground">{plan.empleado_nombre}</p>
            <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
              <span>{plan.cargo_actual ?? "—"}</span>
              <ArrowRight className="size-3.5 shrink-0" />
              <span className="font-medium text-foreground">{plan.cargo_objetivo}</span>
            </div>
          </div>

          {/* Readiness editor */}
          <div className="space-y-2 rounded-xl border bg-muted/30 p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">Readiness</span>
              <span className="text-sm font-semibold tabular-nums text-foreground">
                {readinessEdit}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={readinessEdit}
              onChange={(e) => setReadinessEdit(Number(e.target.value))}
              className="h-2 w-full cursor-pointer accent-primary"
              aria-label="Readiness"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>0%</span><span>50%</span><span>100%</span>
            </div>
            {canWrite && readinessEdit !== plan.readiness && (
              <Button
                size="sm"
                className="mt-1 min-h-8 w-full"
                onClick={guardarReadiness}
                disabled={readinessSaving}
              >
                {readinessSaving ? "Guardando…" : "Guardar readiness"}
              </Button>
            )}
          </div>

          {/* Hitos */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">
                Hitos
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  {plan.hitos_completados}/{plan.hitos_total}
                </span>
              </h3>
              {canWrite && (
                <Button
                  size="sm"
                  variant="outline"
                  className="min-h-8 gap-1.5"
                  onClick={() => setNuevoHitoOpen(true)}
                >
                  <Plus className="size-3.5" />
                  Agregar
                </Button>
              )}
            </div>

            {nuevoHitoOpen && (
              <NuevoHitoForm
                planId={plan.id}
                onCreado={agregarHito}
                onCancelar={() => setNuevoHitoOpen(false)}
              />
            )}

            <HitosList
              hitos={hitos}
              loading={hitosLoading}
              error={hitosError}
              canWrite={canWrite}
              mostrarVacio={!nuevoHitoOpen}
              onCompletar={completar}
            />
          </div>
        </div>
      </div>
    </>
  )
}
