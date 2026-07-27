"use client"

import { Skeleton } from "@/components/ui/skeleton"
import type { Hito } from "@/types/sucesion"

// Lista de hitos del panel de detalle: presentacional puro, con sus 4 estados.
// `mostrarVacio` lo decide el padre (el mensaje de "sin hitos" se oculta mientras el form
// de alta está abierto, igual que antes de la división).
export function HitosList({
  hitos, loading, error, canWrite, mostrarVacio, onCompletar,
}: {
  hitos: Hito[]
  loading: boolean
  error: string | null
  canWrite: boolean
  mostrarVacio: boolean
  onCompletar: (hitoId: string) => void
}) {
  return (
    <>
      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-xl" />
          ))}
        </div>
      )}
      {!loading && error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
      {!loading && !error && hitos.length === 0 && mostrarVacio && (
        <p className="text-sm italic text-muted-foreground">
          Sin hitos aún. Agregá el primero.
        </p>
      )}
      {!loading && hitos.length > 0 && (
        <ul className="space-y-2">
          {hitos.map((hito) => (
            <li key={hito.id} className="flex items-start gap-3 rounded-xl border bg-card p-3">
              {canWrite && (
                <input
                  type="checkbox"
                  checked={hito.completado}
                  disabled={hito.completado}
                  onChange={() => onCompletar(hito.id)}
                  className="mt-0.5 h-4 w-4 cursor-pointer accent-primary disabled:cursor-default"
                  aria-label={`Marcar "${hito.titulo}" como completado`}
                />
              )}
              <div className="min-w-0 flex-1">
                <p className={`text-sm font-medium ${hito.completado ? "text-muted-foreground line-through" : "text-foreground"}`}>
                  {hito.titulo}
                </p>
                {hito.descripcion && (
                  <p className="mt-0.5 text-xs text-muted-foreground">{hito.descripcion}</p>
                )}
                {hito.fecha_objetivo && (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Objetivo: {new Date(hito.fecha_objetivo).toLocaleDateString("es-AR")}
                  </p>
                )}
              </div>
              {hito.completado && (
                <span className="shrink-0 rounded-full bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                  ✓
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
