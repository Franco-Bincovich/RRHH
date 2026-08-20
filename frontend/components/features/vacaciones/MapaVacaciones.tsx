"use client"

import { useMemo, useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { SolicitudVacaciones } from "@/types/vacaciones"
import { MapaLeyenda, CATEGORY_COLORS, deriveVisualCategory } from "./MapaLeyenda"

interface MapaVacacionesProps {
  solicitudes: SolicitudVacaciones[]
}

const MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
const DOW_LABEL = ["D","L","M","X","J","V","S"]

function parseLocalDate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number)
  return new Date(y, m - 1, d)
}

export function MapaVacaciones({ solicitudes }: MapaVacacionesProps) {
  const now = new Date()
  const [año, setAño] = useState(now.getFullYear())
  const [mes, setMes] = useState(now.getMonth())

  const { dayHeaders, rows } = useMemo(() => {
    const numDays = new Date(año, mes + 1, 0).getDate()

    const dayHeaders = Array.from({ length: numDays }, (_, i) => {
      const d = i + 1
      const dow = new Date(año, mes, d).getDay()
      return { d, dow, isWeekend: dow === 0 || dow === 6 }
    })

    const monthStart = new Date(año, mes, 1)
    const monthEnd = new Date(año, mes, numDays)

    const grouped = new Map<string, { nombre: string; dayTypes: Map<number, string> }>()
    for (const s of solicitudes) {
      if (s.cancelada) continue
      const desde = parseLocalDate(s.fecha_desde)
      const hasta = parseLocalDate(s.fecha_hasta)
      if (hasta < monthStart || desde > monthEnd) continue

      if (!grouped.has(s.empleado_id)) {
        grouped.set(s.empleado_id, { nombre: s.empleado_nombre ?? s.empleado_id, dayTypes: new Map() })
      }
      const entry = grouped.get(s.empleado_id)!
      const cat = deriveVisualCategory(s)
      for (const { d } of dayHeaders) {
        const date = new Date(año, mes, d)
        if (date >= desde && date <= hasta) entry.dayTypes.set(d, cat)
      }
    }

    const rows = Array.from(grouped.values()).sort((a, b) => a.nombre.localeCompare(b.nombre))
    return { dayHeaders, rows }
  }, [solicitudes, año, mes])

  function prevMes() {
    if (mes === 0) { setMes(11); setAño(año - 1) }
    else setMes(mes - 1)
  }

  function nextMes() {
    if (mes === 11) { setMes(0); setAño(año + 1) }
    else setMes(mes + 1)
  }

  const selector = (
    <div className="mb-4 flex items-center gap-2">
      <Button variant="outline" size="icon" onClick={prevMes} aria-label="Mes anterior">
        <ChevronLeft className="size-4" />
      </Button>
      <span className="min-w-[170px] text-center text-sm font-medium">
        {MESES[mes]} {año}
      </span>
      <Button variant="outline" size="icon" onClick={nextMes} aria-label="Mes siguiente">
        <ChevronRight className="size-4" />
      </Button>
    </div>
  )

  if (rows.length === 0) {
    return (
      <>
        {selector}
        <div className="rounded-lg border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
          No hay vacaciones que toquen este mes.
        </div>
      </>
    )
  }

  return (
    <>
      {selector}
      <MapaLeyenda />
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="border-collapse text-xs">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-muted border-b border-r border-border min-w-[160px] px-3 py-2 text-left font-medium text-muted-foreground">
                Colaborador
              </th>
              {dayHeaders.map(({ d, dow, isWeekend }) => (
                <th
                  key={d}
                  className={`border-b border-border w-8 min-w-[28px] py-1 text-center font-normal ${isWeekend ? "bg-muted/80 text-muted-foreground/50" : "bg-muted text-muted-foreground"}`}
                >
                  <div>{d}</div>
                  <div className="text-[10px] opacity-60">{DOW_LABEL[dow]}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const isOdd = i % 2 !== 0
              return (
                <tr key={row.nombre}>
                  <td
                    className={`sticky left-0 z-10 border-r border-border/40 px-3 py-1.5 font-medium truncate max-w-[160px] text-sm ${isOdd ? "bg-muted/20" : "bg-background"}`}
                  >
                    {row.nombre}
                  </td>
                  {dayHeaders.map(({ d, isWeekend }) => {
                    const cat = row.dayTypes.get(d)
                    return (
                      <td
                        key={d}
                        className={`h-8 w-8 min-w-[28px] border-r border-border/20 last:border-r-0 ${
                          cat
                            ? (CATEGORY_COLORS[cat as keyof typeof CATEGORY_COLORS] ?? "")
                            : isWeekend
                              ? "bg-muted/40"
                              : isOdd
                                ? "bg-muted/10"
                                : ""
                        }`}
                      />
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </>
  )
}
