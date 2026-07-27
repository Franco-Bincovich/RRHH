"use client"

import { useState } from "react"
import type { Dispatch, SetStateAction } from "react"
import { toast } from "sonner"

import { completarHito, fetchHitos, updateReadiness } from "@/services/sucesion"
import type { Hito, PlanCarrera } from "@/types/sucesion"

// Estado del panel lateral de detalle: hitos del plan abierto y edición de readiness.
// Recibe `setPlanes` para reflejar en la lista los contadores de hitos y el readiness sin
// recargar los planes del backend (mismo comportamiento que antes de la división).
export function usePlanDetalle(setPlanes: Dispatch<SetStateAction<PlanCarrera[]>>) {
  const [selectedPlan, setSelectedPlan]   = useState<PlanCarrera | null>(null)
  const [hitos, setHitos]                 = useState<Hito[]>([])
  const [hitosLoading, setHitosLoading]   = useState(false)
  const [hitosError, setHitosError]       = useState<string | null>(null)
  const [readinessEdit, setReadinessEdit] = useState(0)
  const [readinessSaving, setReadinessSaving] = useState(false)

  /** Deja el plan actualizado en el panel y en la fila de la lista, sin refetch. */
  function sincronizar(updated: PlanCarrera) {
    setSelectedPlan(updated)
    setPlanes((prev) => prev.map((p) => p.id === updated.id ? updated : p))
  }

  function abrir(plan: PlanCarrera) {
    setSelectedPlan(plan)
    setReadinessEdit(plan.readiness)
    setHitos([])
    setHitosError(null)
    setHitosLoading(true)
    fetchHitos(plan.id)
      .then(setHitos)
      .catch(() => setHitosError("No se pudieron cargar los hitos."))
      .finally(() => setHitosLoading(false))
  }

  function cerrar() { setSelectedPlan(null) }

  async function completar(hitoId: string) {
    try {
      await completarHito(hitoId)
      setHitos((prev) => prev.map((h) => h.id === hitoId ? { ...h, completado: true } : h))
      if (selectedPlan) {
        sincronizar({ ...selectedPlan, hitos_completados: selectedPlan.hitos_completados + 1 })
      }
    } catch {
      toast.error("No se pudo completar el hito. Intentá de nuevo.")
    }
  }

  /** Lo llama NuevoHitoForm con el hito ya creado en el backend. */
  function agregarHito(hito: Hito) {
    setHitos((prev) => [...prev, hito])
    if (selectedPlan) sincronizar({ ...selectedPlan, hitos_total: selectedPlan.hitos_total + 1 })
  }

  async function guardarReadiness() {
    if (!selectedPlan || readinessEdit === selectedPlan.readiness) return
    setReadinessSaving(true)
    try {
      sincronizar(await updateReadiness(selectedPlan.id, readinessEdit))
    } catch {
      toast.error("No se pudo guardar el readiness. Intentá de nuevo.")
    }
    finally { setReadinessSaving(false) }
  }

  return {
    selectedPlan, abrir, cerrar,
    hitos, hitosLoading, hitosError, completar, agregarHito,
    readinessEdit, setReadinessEdit, readinessSaving, guardarReadiness,
  }
}

export type PlanDetalle = ReturnType<typeof usePlanDetalle>
