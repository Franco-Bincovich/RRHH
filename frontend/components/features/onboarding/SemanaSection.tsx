"use client"

import { Plus, Trash2 } from "lucide-react"

import { AddTareaForm } from "@/components/features/onboarding/AddTareaForm"
import { InlineEdit } from "@/components/features/onboarding/InlineEdit"
import type { Semana } from "@/components/features/onboarding/_templates_ui"
import type { TemplateTarea } from "@/types/onboarding"

interface SemanaSectionProps {
  templateId: string
  semana: Semana
  /** Tareas de ESTA semana, ya filtradas y ordenadas por el caller. */
  tareas: TemplateTarea[]
  canWrite: boolean
  agregando: boolean
  deletingId: string | null
  onToggleAgregar: () => void
  onTareaAgregada: (t: TemplateTarea) => void
  onGuardarTitulo: (tareaId: string, titulo: string) => Promise<void>
  onGuardarDescripcion: (tareaId: string, descripcion: string) => Promise<void>
  /** Recibe la tarea entera: la confirmación la nombra, no muestra un UUID. */
  onEliminarTarea: (t: TemplateTarea) => void
}

/**
 * Una semana del template: encabezado, sus tareas editables en el lugar y el alta.
 *
 * Presentacional salvo por el POST del alta, que vive en AddTareaForm. Recibe las tareas ya
 * filtradas y ordenadas: quién pertenece a qué semana lo decide la página, que es la que
 * tiene el template entero.
 */
export function SemanaSection({
  templateId,
  semana,
  tareas,
  canWrite,
  agregando,
  deletingId,
  onToggleAgregar,
  onTareaAgregada,
  onGuardarTitulo,
  onGuardarDescripcion,
  onEliminarTarea,
}: SemanaSectionProps) {
  const nextOrden = tareas.length > 0 ? Math.max(...tareas.map((t) => t.orden)) + 1 : 1

  return (
    <section aria-labelledby={`semana-${semana}-title`}>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 id={`semana-${semana}-title`} className="text-sm font-semibold text-foreground">
          Semana {semana}
        </h2>
        {canWrite && (
          <button
            type="button"
            onClick={onToggleAgregar}
            className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Plus className="size-3.5" />
            Agregar tarea
          </button>
        )}
      </div>

      {tareas.length === 0 && !agregando && (
        <p className="rounded-lg border border-dashed px-4 py-3 text-sm text-muted-foreground">
          Sin tareas en esta semana.
        </p>
      )}

      <ul className="space-y-2" role="list">
        {tareas.map((tarea) => (
          <li key={tarea.id} className="rounded-xl border bg-card p-3">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground">
                {tarea.orden}
              </span>
              <div className="min-w-0 flex-1 space-y-1">
                <InlineEdit
                  value={tarea.titulo}
                  onSave={(v) => onGuardarTitulo(tarea.id, v)}
                  className="text-sm font-medium text-foreground"
                  placeholder="Título de la tarea"
                  canEdit={canWrite}
                />
                <InlineEdit
                  value={tarea.descripcion ?? ""}
                  onSave={(v) => onGuardarDescripcion(tarea.id, v)}
                  className="text-xs text-muted-foreground"
                  multiline
                  placeholder="Agregar descripción…"
                  canEdit={canWrite}
                />
              </div>
              {canWrite && (
                <button
                  type="button"
                  onClick={() => onEliminarTarea(tarea)}
                  disabled={deletingId === tarea.id}
                  aria-label="Eliminar tarea"
                  className="flex min-h-8 min-w-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
                >
                  <Trash2 className="size-3.5" />
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      {agregando && (
        <AddTareaForm
          templateId={templateId}
          semana={semana}
          nextOrden={nextOrden}
          onAdded={onTareaAgregada}
          onCancel={onToggleAgregar}
        />
      )}
    </section>
  )
}
