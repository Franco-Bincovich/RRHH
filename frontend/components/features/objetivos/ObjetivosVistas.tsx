"use client"

import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { KanbanView } from "@/components/features/objetivos/KanbanView"
import { ListView } from "@/components/features/objetivos/ListView"
import type { EstadoObjetivo, Objetivo } from "@/types/objetivo"

/**
 * El área de contenido de /objetivos: el selector de vista y lo que cada vista renderiza, con
 * sus estados de carga y de error.
 *
 * Extraído de app/(dashboard)/objetivos/page.tsx, que estaba en 148/150 — dos líneas libres. El
 * movimiento fue PURO: las clases, el `cn()` de la pestaña activa, el orden de las guardas
 * (loading → error → vista) y el skeleton son idénticos a los que estaban en la página.
 *
 * 🔴 POR QUÉ SE EXTRAJO ESTE BLOQUE Y NO EL DE ACCIONES, que era la otra opción.
 * Acá es donde el módulo CRECE: vienen dos vistas más (una anual y otra de tiempo libre), y cada
 * una suma un valor al tipo `Vista`, una etiqueta en la pestaña y una rama de render. Con el
 * bloque en la página, esas tres cosas la empujaban sobre el límite otra vez. El bloque de
 * acciones, en cambio, es estable: son tres botones que no cambian con las vistas nuevas.
 *
 * ⚠️ La etiqueta de la pestaña sigue saliendo del ternario `v === "tablero" ? ... : ...`, tal
 * como estaba en la página: se movió VERBATIM y no se "mejoró" de paso. Con la tercera vista ese
 * ternario deja de servir y hay que cambiarlo por un mapa `Vista → label`; hacerlo ahora habría
 * mezclado un rediseño con una división, que es lo que este corte evita.
 *
 * 🔑 El selector, las guardas y el render viajaron JUNTOS a propósito, aunque en la página
 * estuvieran separados por el `loading`/`error`. Son una sola unidad: agregar una vista sin
 * agregar su pestaña —o al revés— es el bug que este archivo hace imposible de escribir por
 * accidente, porque las dos listas están a la vista una al lado de la otra.
 *
 * Presentacional y controlado: no tiene estado propio, no fetchea. `vista` y su setter, los
 * datos y los handlers los sigue teniendo la página.
 */

export type Vista = "tablero" | "lista"

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}

interface Props {
  vista: Vista
  onVista: (v: Vista) => void
  loading: boolean
  error: boolean
  onReintentar: () => void
  objetivos: Objetivo[]
  /**
   * Cuántas RAÍCES hay en el filtro entero, según el backend. Viaja hasta las dos vistas y no se
   * deriva de `objetivos.length` en ningún lado: hoy coinciden porque este listado no pagina,
   * y el día que pagine `length` es el tamaño de la página. Ver el contrato al pie de
   * `schemas/objetivo.py::ObjetivoListResponse`.
   */
  total: number
  mostrarEmpresa: boolean
  canWrite: boolean
  onMover: (id: string, estado: EstadoObjetivo) => Promise<void>
  moviendo: string | null
  onEdit: (obj: Objetivo) => void
  onDelete: (id: string) => void
  deletingId: string | null
}

export function ObjetivosVistas({
  vista, onVista, loading, error, onReintentar, objetivos, total, mostrarEmpresa,
  canWrite, onMover, moviendo, onEdit, onDelete, deletingId,
}: Props) {
  return (
    <>
      <div className="mb-4 flex gap-1 border-b border-border">
        {(["tablero", "lista"] as Vista[]).map((v) => (
          <button key={v} onClick={() => onVista(v)}
            className={cn("px-4 pb-3 pt-1 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              vista === v ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground")}>
            {v === "tablero" ? "Tablero" : "Lista"}
          </button>
        ))}
      </div>

      {loading && <TableSkeleton />}
      {!loading && error && <div className="py-12 text-center text-sm text-destructive">Error al cargar. <button onClick={onReintentar} className="underline">Reintentar</button></div>}
      {!loading && !error && vista === "tablero" && (
        <KanbanView objetivos={objetivos} total={total} onMover={onMover} moviendo={moviendo}
          canWrite={canWrite} onEdit={onEdit} onDelete={onDelete} deletingId={deletingId} />
      )}
      {!loading && !error && vista === "lista" && (
        <ListView objetivos={objetivos} total={total} showEmpresa={mostrarEmpresa}
          canWrite={canWrite} onEdit={onEdit} onDelete={onDelete} deletingId={deletingId} />
      )}
    </>
  )
}
