"use client"

import { Badge } from "@/components/ui/badge"
import { Select } from "@/components/ui/select"
import type { Resolucion } from "@/services/evaluacionImport"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { EstadoResolucion, EvaluadoPreview } from "@/types/evaluacionImport"

// Lenguaje sin jerga (UX-UI): nada de "sin_candidato".
const ESTADO: Record<EstadoResolucion, { texto: string; variant: "secondary" | "outline" | "destructive" }> = {
  resuelto: { texto: "Asignado", variant: "secondary" },
  ambiguo: { texto: "Varias coincidencias", variant: "outline" },
  sin_candidato: { texto: "No encontramos a esta persona", variant: "destructive" },
}

interface Props {
  ev: EvaluadoPreview
  empleados: EmpleadoSeleccionable[]
  valor: Resolucion
  onChange: (r: Resolucion) => void
}

export function EvaluadoFila({ ev, empleados, valor, onChange }: Props) {
  // Ambiguo → solo los candidatos del backend. Resto → cualquier empleado de la empresa.
  const opciones = ev.estado === "ambiguo"
    ? ev.candidatos.map((c) => ({ id: c.empleado_id, label: `${c.apellido} ${c.nombre}` }))
    : empleados.map((e) => ({ id: e.id, label: `${e.apellido} ${e.nombre}` }))
  const esManual = (valor.empleadoId || "") !== (ev.empleado_id ?? "")
  const info = ESTADO[ev.estado]

  return (
    <div className="space-y-2 rounded-lg border border-border p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium">{ev.apellido_evaluado} {ev.nombre_evaluado}</p>
          <p className="text-xs text-muted-foreground">
            {ev.perfil === "lider" ? "Perfil líder" : "Perfil general"}
            {ev.nota_final != null ? ` · Nota final ${ev.nota_final}` : " · Sin nota final"}
            {ev.gerencia ? ` · ${ev.gerencia}` : ""}
          </p>
        </div>
        <Badge variant={info.variant}>{info.texto}</Badge>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Select
          className="w-auto min-w-64"
          value={valor.empleadoId}
          onChange={(e) => {
            const empleadoId = e.target.value
            const revierte = empleadoId === (ev.empleado_id ?? "")
            onChange({ empleadoId, guardarEquivalencia: revierte ? false : valor.guardarEquivalencia })
          }}
        >
          <option value="">Sin asignar</option>
          {opciones.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
        </Select>
        {esManual && valor.empleadoId && (
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox" checked={valor.guardarEquivalencia}
              onChange={(e) => onChange({ ...valor, guardarEquivalencia: e.target.checked })}
            />
            Recordar esta equivalencia para el próximo ciclo
          </label>
        )}
      </div>
      {ev.motivo && <p className="text-xs text-muted-foreground">{ev.motivo}</p>}
    </div>
  )
}
