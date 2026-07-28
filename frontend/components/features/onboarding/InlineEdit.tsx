"use client"

import { useEffect, useRef, useState } from "react"
import { Check, Pencil, X } from "lucide-react"
import { toast } from "sonner"

interface InlineEditProps {
  value: string
  onSave: (v: string) => Promise<void>
  className?: string
  multiline?: boolean
  placeholder?: string
  canEdit?: boolean
}

/**
 * Texto editable en el lugar: se muestra como texto y pasa a input al hacer clic.
 *
 * `canEdit={false}` lo degrada a texto plano — es el modo en que lo ve un rol de solo lectura,
 * y por eso no alcanza con esconder el botón de guardar: sin el flag el usuario abriría el
 * editor y recién fallaría al guardar.
 */
export function InlineEdit({ value, onSave, className = "", multiline = false, placeholder, canEdit = true }: InlineEditProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const [saving, setSaving] = useState(false)
  const inputRef = useRef<HTMLInputElement & HTMLTextAreaElement>(null)

  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  async function handleSave() {
    if (saving || draft === value) { setEditing(false); return }
    setSaving(true)
    try {
      await onSave(draft)
    } catch {
      toast.error("No se pudo guardar el cambio. Intentá de nuevo.")
    } finally {
      setSaving(false)
      setEditing(false)
    }
  }

  if (!canEdit) {
    return (
      <span className={className}>
        {value || <span className="text-muted-foreground italic">{placeholder}</span>}
      </span>
    )
  }

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => { setDraft(value); setEditing(true) }}
        className={`group flex items-start gap-1.5 text-left ${className}`}
        title="Clic para editar"
      >
        <span>{value || <span className="text-muted-foreground italic">{placeholder}</span>}</span>
        <Pencil className="mt-0.5 size-3.5 shrink-0 opacity-0 group-hover:opacity-60 transition-opacity" />
      </button>
    )
  }

  const sharedClass =
    "w-full rounded-lg border bg-background px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"

  return (
    <div className="flex items-start gap-2">
      {multiline ? (
        <textarea
          ref={inputRef as React.RefObject<HTMLTextAreaElement>}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={3}
          className={`${sharedClass} ${className}`}
          onKeyDown={(e) => { if (e.key === "Escape") setEditing(false) }}
        />
      ) : (
        <input
          ref={inputRef as React.RefObject<HTMLInputElement>}
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className={`${sharedClass} ${className}`}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSave()
            if (e.key === "Escape") setEditing(false)
          }}
        />
      )}
      <div className="mt-1 flex shrink-0 gap-1">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          aria-label="Guardar"
          className="flex min-h-8 min-w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Check className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={() => setEditing(false)}
          aria-label="Cancelar"
          className="flex min-h-8 min-w-8 items-center justify-center rounded-lg border hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <X className="size-3.5" />
        </button>
      </div>
    </div>
  )
}
