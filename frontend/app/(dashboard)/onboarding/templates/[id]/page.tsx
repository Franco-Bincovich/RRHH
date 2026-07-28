"use client"

import { useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft } from "lucide-react"
import { toast } from "sonner"

import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { ErrorState } from "@/components/ui/ErrorState"
import { InlineEdit } from "@/components/features/onboarding/InlineEdit"
import { SemanaSection } from "@/components/features/onboarding/SemanaSection"
import { useTemplateDetalle } from "@/components/features/onboarding/useTemplateDetalle"
import { VisibilidadToggle } from "@/components/features/onboarding/VisibilidadToggle"
import { SEMANAS, type Semana } from "@/components/features/onboarding/_templates_ui"
import { useCanWrite } from "@/hooks/useCanWrite"
import { useUserId } from "@/hooks/useUserId"
import type { TemplateTarea } from "@/types/onboarding"

export default function TemplateDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
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
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded-lg bg-muted" />
        <div className="h-4 w-72 animate-pulse rounded-lg bg-muted" />
        {[1, 2].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
    )
  }

  if (error || !template) {
    return <ErrorState description={error ?? "Template no encontrado"} />
  }

  return (
    <div>
      <div className="mb-6">
        <button
          type="button"
          onClick={() => router.push("/onboarding/templates")}
          className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        >
          <ArrowLeft className="size-4" />
          Volver a templates
        </button>

        <InlineEdit
          value={template.nombre}
          onSave={(v) => guardarCampo("nombre", v)}
          className="text-2xl font-semibold tracking-tight text-foreground"
          placeholder="Nombre del template"
          canEdit={canWrite}
        />
        <div className="mt-1">
          <InlineEdit
            value={template.descripcion ?? ""}
            onSave={(v) => guardarCampo("descripcion", v)}
            className="text-sm text-muted-foreground"
            multiline
            placeholder="Agregar descripción…"
            canEdit={canWrite}
          />
        </div>
        <div className="mt-2 flex items-center gap-3">
          <p className="text-xs text-muted-foreground">
            {template.tareas_total} tarea{template.tareas_total !== 1 ? "s" : ""} en total
          </p>
          {canWrite && (
            <VisibilidadToggle
              templateId={id}
              esPublica={template.es_publica}
              // Sin autor la puede cambiar cualquiera (regla de huérfanas). userId null =
              // todavía no montó: no se habilita hasta saber quién sos.
              puedeCambiar={template.created_by === null || (userId !== null && template.created_by === userId)}
              onCambiada={marcarVisibilidad}
            />
          )}
        </div>
      </div>

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
