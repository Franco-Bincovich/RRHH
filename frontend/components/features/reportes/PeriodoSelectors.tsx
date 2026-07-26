"use client"

// Selectores de período/año de las tarjetas de reporte. Presentacionales (controlados).
const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

export const ANO_ACTUAL = new Date().getFullYear()
export const MES_ACTUAL = new Date().getMonth() + 1
const ANOS = [ANO_ACTUAL, ANO_ACTUAL - 1, ANO_ACTUAL - 2]

export function PeriodoSelector({
  id,
  mes,
  anio,
  onMesChange,
  onAnioChange,
}: {
  id: string
  mes: number
  anio: number
  onMesChange: (mes: number) => void
  onAnioChange: (anio: number) => void
}) {
  return (
    <div className="flex gap-2">
      <div className="flex-1">
        <label htmlFor={`mes-${id}`} className="sr-only">Mes</label>
        <select
          id={`mes-${id}`}
          value={mes}
          onChange={(e) => onMesChange(Number(e.target.value))}
          className="flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-2 py-1 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
        >
          {MESES.map((m, i) => (
            <option key={i + 1} value={i + 1}>{m}</option>
          ))}
        </select>
      </div>
      <div className="w-24">
        <label htmlFor={`anio-${id}`} className="sr-only">Año</label>
        <select
          id={`anio-${id}`}
          value={anio}
          onChange={(e) => onAnioChange(Number(e.target.value))}
          className="flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-2 py-1 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
        >
          {ANOS.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
      </div>
    </div>
  )
}

export function AnioSelector({
  id,
  anio,
  onAnioChange,
}: {
  id: string
  anio: number
  onAnioChange: (anio: number) => void
}) {
  return (
    <div>
      <label htmlFor={`anio-solo-${id}`} className="mb-1 block text-xs font-medium text-foreground">
        Año
      </label>
      <select
        id={`anio-solo-${id}`}
        value={anio}
        onChange={(e) => onAnioChange(Number(e.target.value))}
        className="flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-2 py-1 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
      >
        {ANOS.map((a) => (
          <option key={a} value={a}>{a}</option>
        ))}
      </select>
    </div>
  )
}
