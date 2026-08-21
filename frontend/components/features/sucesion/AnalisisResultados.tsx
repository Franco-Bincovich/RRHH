"use client"

import { Badge } from "@/components/ui/badge"
import { NIVEL_BADGE_CLASS } from "./_sucesion_ui"
import type { EmpleadoAnalisis } from "@/types/sucesion"

/**
 * El RESULTADO del análisis por área: el ranking de colaboradores por score de assessment.
 *
 * 🔴 Salió de `AnalisisAreaModal.tsx` porque ese archivo llegaba a 158 líneas contra un límite de
 * 150. El corte es por responsabilidad: el modal PIDE el análisis (el selector, el botón, el
 * estado de carga y el error) y esto MUESTRA lo que volvió.
 */

function nivelBadge(nivel: string | null) {
  if (!nivel) return null
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${NIVEL_BADGE_CLASS[nivel] ?? "bg-muted text-muted-foreground"}`}>
{nivel}
    </span>
  )
}

export function AnalisisResultados({ res }: { res: EmpleadoAnalisis[] }) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-foreground">
        {res.length === 0
          ? "No hay colaboradores en esta área."
          : `${res.length} colaborador${res.length !== 1 ? "es" : ""} encontrado${res.length !== 1 ? "s" : ""}`}
      </p>
      {res.length > 0 && (
        <ul className="max-h-64 divide-y divide-border overflow-y-auto rounded-lg border">
          {res.map((emp, idx) => (
            <li key={emp.id} className="flex items-center gap-3 px-3 py-2.5">
              <span className="w-5 shrink-0 text-center text-xs font-semibold text-muted-foreground">
                {idx + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">
                  {emp.nombre} {emp.apellido}
                </p>
                {emp.cargo && (
                  <p className="truncate text-xs text-muted-foreground">{emp.cargo}</p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                {/* 🔴 EL SCORE DEJÓ DE PINTARSE CON EL COLOR DE LA MARCA. `variant="default"`
                    es el relleno `bg-primary`, que en este sistema está reservado para el
                    chip de filtro activo y para la acción principal: un número que se
                    repite en cada fila teñido de ese color le saca el énfasis justamente a
                    lo que sí es accionable. Contorno con cifras tabulares, que además
                    alinea los dígitos entre filas y hace comparable la columna. */}
                {emp.score != null
                  ? <Badge variant="outline" className="tabular-nums">{emp.score}</Badge>
                  : <Badge variant="outline" className="text-muted-foreground">Sin score</Badge>
                }
                {nivelBadge(emp.potencial)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
