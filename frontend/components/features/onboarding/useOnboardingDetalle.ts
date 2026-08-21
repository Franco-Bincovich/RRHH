"use client"

import { useState } from "react"

import { fetchOnboardingEmpleado } from "@/services/onboarding"
import type { OnboardingDetalle, OnboardingInstancia } from "@/types/onboarding"

/**
 * El DETALLE de un onboarding: qué proceso está abierto en el panel lateral y el update optimista
 * de sus tareas.
 *
 * Salió de `app/(dashboard)/onboarding/page.tsx` al migrarla al patrón del bloque B. Ese archivo
 * estaba en **396 líneas contra un límite de 150** —deuda anotada en CLAUDE.md— y los estados
 * nuevos lo llevaban a 404. Es el cuarto y último corte: con `IniciarOnboardingModal`,
 * `OnboardingList` y `OnboardingAcciones`, la página quedó adentro del límite por primera vez.
 *
 * 🔴 EL TOGGLE DE UNA TAREA ACTUALIZA DOS COSAS A LA VEZ, y por eso vive junto: el detalle abierto
 * y la fila de la lista de atrás. Si sólo se refrescara el detalle, la tarjeta seguiría diciendo
 * el porcentaje viejo hasta la próxima carga — dos números distintos para el mismo proceso, en la
 * misma pantalla. Por eso el hook recibe `setOnboardings`: no puede hacer una sin la otra.
 *
 * ⚠️ El fallo al traer el detalle se traga a propósito: no bloquea la lista, que es lo que el
 * usuario está mirando. Es la única excepción declarada al "un error nunca se descarta en
 * silencio" del repo, y sobrevive porque el costo de equivocarse es un panel que no abre, no un
 * dato falso en pantalla.
 */
export function useOnboardingDetalle(
  setOnboardings: (fn: (prev: OnboardingInstancia[]) => OnboardingInstancia[]) => void,
) {
  const [detalle, setDetalle] = useState<OnboardingDetalle | null>(null)
  const [loadingDetalle, setLoadingDetalle] = useState(false)
  async function handleSelect(empleadoId: string) {
    if (detalle?.empleado_id === empleadoId) {
      setDetalle(null)
      return
    }
    setLoadingDetalle(true)
    try {
      const d = await fetchOnboardingEmpleado(empleadoId)
      setDetalle(d)
    } catch {
      // Silently fail — no bloquea la lista
    } finally {
      setLoadingDetalle(false)
    }
  }

  function handleTareaToggled(tareaId: string, completada: boolean) {
    if (!detalle) return
    const updatedTareas = detalle.tareas.map((t) =>
      t.tarea_id === tareaId ? { ...t, completada } : t,
    )
    const done = updatedTareas.filter((t) => t.completada).length
    const total = updatedTareas.length
    const pct = total > 0 ? Math.round((done / total) * 100) : 0
    setDetalle({ ...detalle, tareas: updatedTareas, progreso: pct, tareas_completadas: done })
    setOnboardings((prev) =>
      prev.map((o) =>
        o.empleado_id === detalle.empleado_id
          ? { ...o, progreso: pct, tareas_completadas: done }
          : o,
      ),
    )
  }

  return { detalle, setDetalle, loadingDetalle, handleSelect, handleTareaToggled }
}
