"use client"

import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { EstadoConteo, ProcesoResumen } from "@/services/procesos"

/**
 * 🔴 LOS PUNTOS DEJARON DE PINTARSE CON LA PALETA CRUDA DE TAILWIND. Eran `bg-blue-500`,
 * `bg-green-500`, `bg-red-500`, `bg-slate-300/400` y `bg-amber-500`: cinco colores elegidos a
 * mano que no salían de ningún token y que, en particular, ponían **azul sobre un dato** — el
 * color que en el resto del sistema significa "acción" y que `docs/SISTEMA-DE-DISENO.md` §3
 * reserva para el chip de filtro. Ahora salen de los mismos pares que todos los estados de la
 * app, medidos en los dos temas por `app/contrasteTokens.test.ts`.
 *
 * ⚠️ ESTE MAPA CRUZA MÓDULOS: las claves son los estados de onboarding, offboarding, vacantes,
 * objetivos y formación juntos, con nombres que a veces coinciden y a veces no ("terminado" y
 * "finalizada" son el mismo desenlace). Por eso la escala se define por lo que el estado
 * SIGNIFICA para quien mira el panel, y no por el módulo del que viene:
 *   · **en curso** → ATENCIÓN. Es trabajo abierto: lo que el panel existe para que se vea.
 *   · **terminado** → ÉXITO.
 *   · **cancelado** → PELIGRO.
 *   · **pendiente / cerrado** → NEUTRO. Ni arrancó, o ya no está en juego.
 */
export const ESTADO_COLOR: Record<string, string> = {
  en_progreso: "bg-warning",
  iniciado:    "bg-warning",
  en_curso:    "bg-warning",
  haciendo:    "bg-warning",
  abierto:     "bg-warning",
  en_revision: "bg-warning",
  nueva:       "bg-muted-foreground/60",
  completado:  "bg-success",
  finalizada:  "bg-success",
  terminado:   "bg-success",
  cerrada:     "bg-muted-foreground/60",
  pendiente:   "bg-muted-foreground/40",
  por_hacer:   "bg-muted-foreground/40",
  cancelado:   "bg-destructive",
  cancelada:   "bg-destructive",
}

export function EstadoRow({ ec }: { ec: EstadoConteo }) {
  return (
    <div className="flex items-center justify-between py-1">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "size-2 shrink-0 rounded-full",
            ESTADO_COLOR[ec.estado] ?? "bg-muted",
          )}
        />
        <span className="text-sm text-muted-foreground">{ec.label}</span>
      </div>
      <span className="text-sm font-semibold tabular-nums text-foreground">
        {ec.total}
      </span>
    </div>
  )
}

export function ProcesoCard({ proceso }: { proceso: ProcesoResumen }) {
  return (
    <Card padding="sm" interactive className="flex flex-col">
      <div className="mb-4 flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-foreground">{proceso.label}</h3>
        <span className="shrink-0 text-2xl font-bold tabular-nums text-foreground">
          {proceso.total}
        </span>
      </div>
      <div className="divide-y divide-border">
        {proceso.estados.map((ec) => (
          <EstadoRow key={ec.estado} ec={ec} />
        ))}
      </div>
    </Card>
  )
}

