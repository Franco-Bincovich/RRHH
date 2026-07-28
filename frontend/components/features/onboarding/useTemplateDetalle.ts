"use client"

import { useEffect, useState } from "react"

import { deleteTarea, fetchTemplate, updateTarea, updateTemplate } from "@/services/onboarding"
import type { OnboardingTemplate, TemplateTarea } from "@/types/onboarding"

/** Campos de texto de una tarea que el detalle deja editar en el lugar. */
type CampoTarea = "titulo" | "descripcion"

/**
 * Carga y mutación de un template de onboarding. Molde: usePlanDetalle de sucesión.
 *
 * Cada mutación aplica el cambio sobre el estado local en vez de recargar el template entero:
 * el detalle es un formulario de edición en el lugar, y un refetch por cada tecla de InlineEdit
 * haría parpadear la pantalla. Los `set` propagan lo que devolvió el backend, no el borrador,
 * así que si el servidor normaliza un valor se ve el normalizado.
 *
 * Las funciones de guardado NO atrapan el error: lo hace InlineEdit, que es quien sabe volver
 * al modo edición y mostrar el toast. `eliminarTarea` sí lo atrapa porque no tiene arriba a
 * nadie que lo haga.
 */
export function useTemplateDetalle(id: string) {
  const [template, setTemplate] = useState<OnboardingTemplate | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchTemplate(id)
      .then(setTemplate)
      .catch(() => setError("No se pudo cargar el template"))
      .finally(() => setLoading(false))
  }, [id])

  async function guardarNombre(nombre: string) {
    const updated = await updateTemplate(id, { nombre })
    setTemplate((prev) => prev ? { ...prev, nombre: updated.nombre } : prev)
  }

  async function guardarDescripcion(descripcion: string) {
    const updated = await updateTemplate(id, { descripcion })
    setTemplate((prev) => prev ? { ...prev, descripcion: updated.descripcion } : prev)
  }

  /** Un solo camino para los campos de texto de una tarea: sumar un cuarto es un call site. */
  async function guardarCampoTarea(tareaId: string, campo: CampoTarea, valor: string) {
    const updated = await updateTarea(id, tareaId, { [campo]: valor })
    setTemplate((prev) =>
      prev
        ? { ...prev, tareas: prev.tareas.map((t) => t.id === tareaId ? { ...t, [campo]: updated[campo] } : t) }
        : prev
    )
  }

  async function eliminarTarea(tareaId: string): Promise<boolean> {
    try {
      await deleteTarea(id, tareaId)
      setTemplate((prev) =>
        prev
          ? { ...prev, tareas: prev.tareas.filter((t) => t.id !== tareaId), tareas_total: prev.tareas_total - 1 }
          : prev
      )
      return true
    } catch {
      return false
    }
  }

  function agregarTarea(tarea: TemplateTarea) {
    setTemplate((prev) =>
      prev ? { ...prev, tareas: [...prev.tareas, tarea], tareas_total: prev.tareas_total + 1 } : prev
    )
  }

  return { template, loading, error, guardarNombre, guardarDescripcion, guardarCampoTarea, eliminarTarea, agregarTarea }
}
