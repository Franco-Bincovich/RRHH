"use client"

import { Trash2 } from "lucide-react"

import { AccionFila } from "@/components/ui/AccionFila"
import type { Hora } from "@/types/proyecto"

const ARS = new Intl.NumberFormat("es-AR", {
  style: "currency", currency: "ARS", maximumFractionDigits: 0,
})

function formatFecha(iso: string) {
  return new Date(iso + "T00:00:00")
    .toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

/**
 * Una carga de horas del proyecto, como fila.
 *
 * Salió de `HorasTab.tsx`, que quedaba en 171 contra el tope de 150 al migrar su borrado del
 * `confirm()` del navegador a `<ConfirmDialog>` (que trae el hook del pendiente, el flag de "en
 * vuelo" y el diálogo). El corte es por RESPONSABILIDAD y no sólo por líneas: acá está cómo se
 * MUESTRA una carga, allá cuándo se piden, se crean y se borran.
 *
 * 🔴 EL BOTÓN DE BAJA NO EJECUTA: PIDE. `onPedirBaja` abre el diálogo; el borrado real lo hace el
 * tab. Es la única forma de que la fila no tenga que conocer el service ni el estado de carga —
 * y es lo que hace que el `confirm()` del navegador no pueda volver por esta puerta.
 */
export function HoraFila({ hora, canWrite, onPedirBaja }: {
  hora: Hora
  canWrite: boolean
  onPedirBaja: (h: Hora) => void
}) {
  return (
    <div className="group flex items-center justify-between gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-medium text-foreground">{hora.empleado_nombre}</span>
          {hora.empleado_empresa_nombre && (
            <span className="text-xs text-muted-foreground">· {hora.empleado_empresa_nombre}</span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {formatFecha(hora.fecha)} · {hora.horas}h
          {hora.valor_hora_snapshot !== null ? ` · ${ARS.format(hora.valor_hora_snapshot)}/h` : ""}
          {hora.descripcion ? ` · ${hora.descripcion}` : ""}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <span className="text-sm font-semibold tabular-nums text-foreground">
          {/* "—" y no "$ 0": una carga sin `valor_hora_snapshot` no se puede costear, que no es
              lo mismo que haber costado cero. */}
          {hora.costo !== null ? ARS.format(hora.costo) : "—"}
        </span>
        {canWrite && (
          <AccionFila
            tono="destructivo"
            aria-label={`Eliminar la carga de ${hora.horas}h del ${formatFecha(hora.fecha)}`}
            onClick={() => onPedirBaja(hora)}
          >
            <Trash2 className="size-4" aria-hidden="true" />
          </AccionFila>
        )}
      </div>
    </div>
  )
}
