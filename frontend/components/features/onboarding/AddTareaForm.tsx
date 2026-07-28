"use client"

import { useState } from "react"

import { addTarea } from "@/services/onboarding"
import type { Semana } from "@/components/features/onboarding/_templates_ui"
import type { TemplateTarea } from "@/types/onboarding"

interface AddTareaFormProps {
  templateId: string
  semana: Semana
  nextOrden: number
  onAdded: (t: TemplateTarea) => void
  onCancel: () => void
}

/**
 * Alta de una tarea dentro de una semana del template. Autocontenido: hace su propio POST y
 * devuelve la tarea creada por `onAdded`. El `nextOrden` lo calcula el caller, que es quien
 * conoce las tareas ya cargadas de esa semana.
 */
export function AddTareaForm({ templateId, semana, nextOrden, onAdded, onCancel }: AddTareaFormProps) {
  const [titulo, setTitulo] = useState("")
  const [descripcion, setDescripcion] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleAdd() {
    if (!titulo.trim() || saving) return
    setSaving(true)
    setError(null)
    try {
      const t = await addTarea(templateId, {
        titulo: titulo.trim(),
        descripcion: descripcion.trim() || undefined,
        semana,
        orden: nextOrden,
      })
      onAdded(t)
    } catch {
      setError("No se pudo agregar la tarea.")
      setSaving(false)
    }
  }

  return (
    <div className="mt-2 rounded-lg border bg-muted/30 p-3 space-y-2">
      <input
        type="text"
        value={titulo}
        onChange={(e) => setTitulo(e.target.value)}
        placeholder="Título de la tarea"
        autoFocus
        className="w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); if (e.key === "Escape") onCancel() }}
      />
      <textarea
        value={descripcion}
        onChange={(e) => setDescripcion(e.target.value)}
        placeholder="Descripción (opcional)"
        rows={2}
        className="w-full rounded-lg border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={handleAdd}
          disabled={!titulo.trim() || saving}
          className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {saving ? "Agregando…" : "Agregar tarea"}
        </button>
      </div>
    </div>
  )
}
