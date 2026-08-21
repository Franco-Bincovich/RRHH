"use client"

import { useState } from "react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { cn } from "@/lib/utils"

// La grilla y sus colores viven aparte: ver el 🔴 del encabezado de ese archivo.
import { CELDAS, ZONE_BG, ZONE_TEXT, initials, type EmpleadoCelda, type Zone } from "./_nineBoxGrilla"

// `EmpleadoCelda` se mudó con la grilla —es la forma del DATO que cada casillero recibe, no del
// componente— y se re-exporta desde acá para que los dos importadores que ya existían
// (`_sucesion_ui.ts` y `MapaTalentoTab.tsx`) no tengan que cambiar de origen.
export type { EmpleadoCelda } from "./_nineBoxGrilla"

// ─── Component ────────────────────────────────────────────────────────────────

interface NineBoxProps {
  empleados: EmpleadoCelda[]
}

export function NineBox({ empleados }: NineBoxProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  function toggle(id: string) {
    setSelectedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="select-none">
      <div className="flex gap-2">
        {/* ── Y-axis ──────────────────────────────────────────────────────── */}
        <div className="flex shrink-0 items-stretch">
          {/* Rotated title */}
          <div className="flex w-5 items-center justify-center">
            <span className="-rotate-90 whitespace-nowrap text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Potencial
            </span>
          </div>
          {/* Row labels */}
          <div className="flex w-10 flex-col justify-around pr-1 text-right text-xs text-muted-foreground">
            <span>Alto</span>
            <span>Medio</span>
            <span>Bajo</span>
          </div>
        </div>

        {/* ── Grid + X-axis ───────────────────────────────────────────────── */}
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          {/* 3 × 3 grid */}
          <div className="grid grid-cols-3 gap-1">
            {CELDAS.map((celda) => {
              const emps = empleados.filter(
                (e) => e.fila === celda.fila && e.columna === celda.columna,
              )
              return (
                <div
                  key={`${celda.fila}-${celda.columna}`}
                  className={cn(
                    "min-h-[100px] rounded-lg border p-2",
                    ZONE_BG[celda.zone],
                  )}
                >
                  <p
                    className={cn(
                      "mb-2 text-[10px] font-semibold uppercase tracking-wide",
                      ZONE_TEXT[celda.zone],
                    )}
                  >
                    {celda.nombre}
                  </p>

                  <div className="flex flex-wrap gap-2">
                    {emps.map((emp) => (
                      <div key={emp.id} className="relative">
                        {/* Backdrop — closes tooltip when clicking outside */}
                        {selectedId === emp.id && (
                          <div
                            className="fixed inset-0 z-10"
                            onClick={() => setSelectedId(null)}
                          />
                        )}

                        <button
                          onClick={() => toggle(emp.id)}
                          className="relative z-20 flex flex-col items-center gap-0.5 rounded p-0.5 outline-none ring-primary/50 focus-visible:ring-2"
                          aria-expanded={selectedId === emp.id}
                          aria-label={`${emp.nombre} — ${emp.cargo}`}
                        >
                          <Avatar size="sm">
                            <AvatarFallback>{initials(emp.nombre)}</AvatarFallback>
                          </Avatar>
                          <span className="w-14 truncate text-center text-[9px] leading-tight text-foreground">
                            {emp.nombre.split(" ")[0]}
                          </span>
                        </button>

                        {/* Tooltip */}
                        {selectedId === emp.id && (
                          <div className="absolute bottom-full left-1/2 z-30 mb-2 w-44 -translate-x-1/2 rounded-lg border bg-popover p-2.5 shadow-lg">
                            <p className="text-xs font-semibold text-foreground">
                              {emp.nombre}
                            </p>
                            <p className="mt-0.5 text-xs text-muted-foreground">
                              {emp.cargo}
                            </p>
                            <p className="text-xs text-muted-foreground">{emp.area}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>

          {/* X-axis labels */}
          <div className="grid grid-cols-3 gap-1 text-center text-xs text-muted-foreground">
            <span>Bajo</span>
            <span>Medio</span>
            <span>Alto</span>
          </div>
          <p className="text-center text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Desempeño →
          </p>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-3">
        {(["verde", "amarillo", "rojo"] as Zone[]).map((zone) => (
          <div key={zone} className="flex items-center gap-1.5">
            <div className={cn("size-2.5 rounded-sm border", ZONE_BG[zone])} />
            <span className="text-xs text-muted-foreground capitalize">
              {zone === "verde" ? "Alto impacto" : zone === "amarillo" ? "Zona media" : "Requiere atención"}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
