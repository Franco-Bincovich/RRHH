"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { toast } from "sonner"

import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { SemanaSection } from "@/components/features/onboarding/SemanaSection"
import { useTemplateDetalle } from "@/components/features/onboarding/useTemplateDetalle"
import { VisibilidadToggle } from "@/components/features/onboarding/VisibilidadToggle"
import { BarraTemplate } from "@/components/features/onboarding/ficha/BarraTemplate"
import { SEMANAS, type Semana } from "@/components/features/onboarding/_templates_ui"
import { useCanWrite } from "@/hooks/useCanWrite"
import { useUserId } from "@/hooks/useUserId"
import type { TemplateTarea } from "@/types/onboarding"

export default function TemplateDetailPage() {
  const { id } = useParams<{ id: string }>()
  const canWrite = useCanWrite()
  const userId = useUserId()
  const {
    template, loading, error,
    guardarCampo, marcarVisibilidad, guardarCampoTarea, eliminarTarea, agregarTarea,
  } = useTemplateDetalle(id)
  const [addingSemana, setAddingSemana] = useState<Semana | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [tareaAEliminar, setTareaAEliminar] = useState<TemplateTarea | null>(null)

  async function confirmarEliminarTarea() {
    if (!tareaAEliminar) return
    setDeletingId(tareaAEliminar.id)
    if (await eliminarTarea(tareaAEliminar.id)) {
      toast.success("Tarea eliminada")
      setTareaAEliminar(null)
    } else {
      toast.error("No se pudo eliminar la tarea.")
    }
    setDeletingId(null)
  }

  if (loading) {
    // El esqueleto tiene la grilla exacta (§3): la barra de identidad y las cuatro semanas.
    return (
      <div>
        <Skeleton shimmer className="mb-4 h-[118px] w-full rounded-xl" />
        <div className="space-y-6">
          {SEMANAS.map((s) => <Skeleton key={s} shimmer className="h-32 w-full rounded-xl" />)}
        </div>
      </div>
    )
  }

  if (error || !template) {
    return <ErrorState description={error ?? "Template no encontrado"} />
  }

  return (
    <div>
      {/* La ÚNICA acción de esta ficha es cambiar la visibilidad, así que es la primaria y va
          última por construcción (§3). El chip de al lado del título dice el mismo estado y eso
          es a propósito — el porqué está en `BarraTemplate`. */}
      <BarraTemplate
        template={template}
        canWrite={canWrite}
        onGuardarCampo={guardarCampo}
        acciones={canWrite ? (
          <VisibilidadToggle
            templateId={id}
            esPublica={template.es_publica}
            // Sin autor la puede cambiar cualquiera (regla de huérfanas). userId null =
            // todavía no montó: no se habilita hasta saber quién sos.
            puedeCambiar={template.created_by === null || (userId !== null && template.created_by === userId)}
            onCambiada={marcarVisibilidad}
          />
        ) : undefined}
      />

      <div className="space-y-6">
        {SEMANAS.map((semana) => (
          <SemanaSection
            key={semana}
            templateId={id}
            semana={semana}
            tareas={template.tareas.filter((t) => t.semana === semana).sort((a, b) => a.orden - b.orden)}
            canWrite={canWrite}
            agregando={addingSemana === semana}
            deletingId={deletingId}
            onToggleAgregar={() => setAddingSemana(addingSemana === semana ? null : semana)}
            onTareaAgregada={(t) => { agregarTarea(t); setAddingSemana(null) }}
            onGuardarTitulo={(tareaId, v) => guardarCampoTarea(tareaId, "titulo", v)}
            onGuardarDescripcion={(tareaId, v) => guardarCampoTarea(tareaId, "descripcion", v)}
            onEliminarTarea={setTareaAEliminar}
          />
        ))}
      </div>

      <ConfirmDialog
        open={tareaAEliminar !== null}
        onClose={() => setTareaAEliminar(null)}
        onConfirm={confirmarEliminarTarea}
        title="Eliminar tarea"
        description={`Se quitará "${tareaAEliminar?.titulo ?? ""}" del template. Los onboardings ya iniciados con este template conservan su copia de la tarea.`}
        confirmLabel="Eliminar"
        loading={deletingId !== null}
      />
    </div>
  )
}
