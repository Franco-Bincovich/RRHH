"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

interface CampoBase {
  id: string
  etiqueta: string
  /** Qué significa el valor. Va debajo del campo, no en un tooltip: son reglas de negocio
   *  que quien las configura necesita leer sin tener que descubrir el hover. */
  ayuda?: string
  /** En solo lectura el campo se muestra deshabilitado en vez de ocultarse: el VALOR es
   *  información útil para un rol que puede leer configuración pero no escribirla. */
  editable: boolean
}

export function CampoNumero({
  id, etiqueta, ayuda, editable, valor, onChange, min, max, sufijo,
}: CampoBase & {
  valor: number
  onChange: (v: number) => void
  min: number
  max: number
  sufijo?: string
}) {
  return (
    <div>
      <Label htmlFor={id} className="mb-1.5 block text-sm">{etiqueta}</Label>
      <div className="flex items-center gap-2">
        <Input
          id={id}
          type="number"
          inputMode="numeric"
          min={min}
          max={max}
          disabled={!editable}
          value={valor}
          // Number("") es 0 y pasaría un 0 silencioso al form; NaN lo descarta y deja el
          // valor anterior, que es lo que el usuario ve mientras borra para retipear.
          onChange={(e) => {
            const n = Number(e.target.value)
            if (!Number.isNaN(n)) onChange(n)
          }}
          className="w-28"
        />
        {sufijo && <span className="text-sm text-muted-foreground">{sufijo}</span>}
      </div>
      {ayuda && <p className="mt-1 text-xs text-muted-foreground">{ayuda}</p>}
    </div>
  )
}

export function CampoMes({
  id, etiqueta, ayuda, editable, valor, onChange,
}: CampoBase & { valor: number; onChange: (v: number) => void }) {
  return (
    <div>
      <Label htmlFor={id} className="mb-1.5 block text-sm">{etiqueta}</Label>
      <select
        id={id}
        disabled={!editable}
        value={valor}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm disabled:opacity-50"
      >
        {MESES.map((m, i) => (
          <option key={m} value={i + 1}>{m}</option>
        ))}
      </select>
      {ayuda && <p className="mt-1 text-xs text-muted-foreground">{ayuda}</p>}
    </div>
  )
}
