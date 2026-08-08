"use client"

import { useMemo } from "react"
import { Badge } from "@/components/ui/badge"
import { ObjetivoCard } from "@/components/features/objetivos/ObjetivoCard"
import type { EstadoObjetivo, Objetivo } from "@/types/objetivo"

const ESTADOS: EstadoObjetivo[] = ["por_hacer", "haciendo", "terminado"]

const ESTADO_LABELS: Record<EstadoObjetivo, string> = {
  por_hacer: "Por hacer",
  haciendo:  "Haciendo",
  terminado: "Terminado",
}

const ESTADO_COLUMN_BG: Record<EstadoObjetivo, string> = {
  por_hacer: "bg-slate-50 dark:bg-slate-800/40",
  haciendo:  "bg-blue-50 dark:bg-blue-900/20",
  terminado: "bg-emerald-50 dark:bg-emerald-900/20",
}

const ESTADO_DOT: Record<EstadoObjetivo, string> = {
  por_hacer: "bg-slate-400",
  haciendo:  "bg-blue-500",
  terminado: "bg-emerald-500",
}

interface Props {
  objetivos:  Objetivo[]
  onMover:    (id: string, estado: EstadoObjetivo) => Promise<void>
  moviendo:   string | null
  canWrite:   boolean
  onEdit:     (obj: Objetivo) => void
  onDelete:   (id: string) => void
  deletingId: string | null
}

export function KanbanView({ objetivos, onMover, moviendo, canWrite, onEdit, onDelete, deletingId }: Props) {
  const porEstado = useMemo(() => {
    const map: Record<EstadoObjetivo, Objetivo[]> = { por_hacer: [], haciendo: [], terminado: [] }
    // 🔴 SOLO RAÍCES. El backend ya devuelve el árbol (los hijos vienen anidados en `hijos`),
    // pero el filtro va igual: un hijo que se colara acá sería una tarjeta suelta, y peor,
    // sumaría al contador de su columna — "8 objetivos" pasaría a contar subtareas. La
    // cantidad de hijos se muestra como badge en la tarjeta del padre (ObjetivoCard).
    for (const obj of objetivos) if (!obj.parent_id) map[obj.estado]?.push(obj)
    return map
  }, [objetivos])

  return (
    <div className="overflow-x-auto pb-4">
      <div className="flex gap-4" style={{ width: "max-content" }}>
        {ESTADOS.map((estado) => {
          const cards     = porEstado[estado]
          const prevEstado = ESTADOS[ESTADOS.indexOf(estado) - 1] as EstadoObjetivo | undefined
          const nextEstado = ESTADOS[ESTADOS.indexOf(estado) + 1] as EstadoObjetivo | undefined
          return (
            <div key={estado} className={`flex w-72 flex-shrink-0 flex-col rounded-xl p-3 ${ESTADO_COLUMN_BG[estado]}`}>
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`size-2 rounded-full ${ESTADO_DOT[estado]}`} />
                  <span className="text-sm font-semibold text-foreground">{ESTADO_LABELS[estado]}</span>
                </div>
                <Badge variant="secondary">{cards.length}</Badge>
              </div>
              <div className="flex flex-col gap-2">
                {cards.map((obj) => (
                  <div key={obj.id}>
                    <ObjetivoCard objetivo={obj} canWrite={canWrite} onEdit={onEdit} onDelete={onDelete} deletingId={deletingId} />
                    <div className="mt-1 flex gap-1">
                      {canWrite && prevEstado && (
                        <button
                          disabled={moviendo === obj.id}
                          onClick={() => onMover(obj.id, prevEstado)}
                          className="flex-1 rounded py-1 px-2 text-left text-xs text-muted-foreground transition-colors hover:bg-background/80 hover:text-foreground disabled:opacity-50"
                        >
                          ← {ESTADO_LABELS[prevEstado]}
                        </button>
                      )}
                      {canWrite && nextEstado && (
                        <button
                          disabled={moviendo === obj.id}
                          onClick={() => onMover(obj.id, nextEstado)}
                          className="flex-1 rounded py-1 px-2 text-right text-xs text-muted-foreground transition-colors hover:bg-background/80 hover:text-foreground disabled:opacity-50"
                        >
                          {ESTADO_LABELS[nextEstado]} →
                        </button>
                      )}
                    </div>
                  </div>
                ))}
                {cards.length === 0 && (
                  <div className="rounded-lg border border-dashed border-border bg-background/50 p-4 text-center text-xs text-muted-foreground">
                    Sin objetivos
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
