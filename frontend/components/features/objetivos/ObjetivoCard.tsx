"use client"

import { Pencil, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { Objetivo, PrioridadObjetivo } from "@/types/objetivo"

const PRIORIDAD_LABEL: Record<PrioridadObjetivo, string> = { baja: "Baja", media: "Media", alta: "Alta" }

const PRIORIDAD_CLASS: Record<PrioridadObjetivo, string> = {
  baja:  "border-border bg-transparent text-muted-foreground",
  media: "border-primary/40 bg-primary/10 text-primary",
  alta:  "border-destructive/40 bg-destructive/10 text-destructive",
}

function isOverdue(fecha: string | null, estado: string): boolean {
  if (!fecha || estado === "terminado") return false
  return fecha < new Date().toISOString().slice(0, 10)
}

function formatDate(s: string) {
  const [y, m, d] = s.split("-"); return `${d}/${m}/${y}`
}

interface Props {
  objetivo: Objetivo
  canWrite: boolean
  onEdit: (obj: Objetivo) => void
  onDelete: (id: string) => void
  deletingId: string | null
}

export function ObjetivoCard({ objetivo: obj, canWrite, onEdit, onDelete, deletingId }: Props) {
  const atrasado = isOverdue(obj.fecha_entrega, obj.estado)

  return (
    <div className="rounded-lg border border-border bg-background p-3 shadow-sm">
      <div className="mb-1.5 flex items-start justify-between gap-1">
        <p className="text-sm font-medium leading-snug text-foreground">{obj.titulo}</p>
        {canWrite && (
          <div className="flex shrink-0 items-center gap-0.5">
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => onEdit(obj)} aria-label="Editar">
              <Pencil className="size-3" />
            </Button>
            <Button
              variant="ghost" size="sm" className="h-6 w-6 p-0 text-destructive hover:text-destructive"
              disabled={deletingId === obj.id} onClick={() => onDelete(obj.id)} aria-label="Eliminar"
            >
              <Trash2 className="size-3" />
            </Button>
          </div>
        )}
      </div>
      {/* El dueño con nombre y, si hay más, cuántos: la lista completa no entra en una
          tarjeta de 288px y el dueño es quien responde por el objetivo. */}
      <p className="mb-2 text-xs text-muted-foreground">
        {obj.responsable_nombre ?? "—"}
        {obj.responsables.length > 1 && ` +${obj.responsables.length - 1}`}
      </p>
      <div className="flex items-center gap-2">
        <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium ${PRIORIDAD_CLASS[obj.prioridad]}`}>
          {PRIORIDAD_LABEL[obj.prioridad]}
        </span>
        {obj.fecha_entrega && (
          <span className={`text-[11px] ${atrasado ? "font-semibold text-destructive" : "text-muted-foreground"}`}>
            {atrasado ? "⚠ " : ""}{formatDate(obj.fecha_entrega)}
          </span>
        )}
        {/* 🔴 Los subobjetivos NO son tarjetas: se cuentan acá. Una tarjeta por hijo llenaría
            la columna de tareas sueltas y el contador del kanban dejaría de decir cuántos
            objetivos hay. El detalle de cada hijo vive en la vista de Lista. */}
        {obj.hijos.length > 0 && (
          <span
            className="inline-flex items-center rounded-md border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground"
            title={`${obj.hijos.length} subobjetivo${obj.hijos.length !== 1 ? "s" : ""}`}
          >
            ⌄ {obj.hijos.length}
          </span>
        )}
      </div>
    </div>
  )
}
