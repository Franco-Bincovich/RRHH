"use client"

import { ANIOS, MESES_LARGOS } from "@/components/features/costos/formatos"
import { Select } from "@/components/ui/select"

/**
 * Selector de mes y año de la pantalla de Costos. Presentacional y controlado: no tiene estado
 * propio ni fetchea.
 *
 * Movido VERBATIM desde `costos/page.tsx` al partirla (624 → orquestador). Las clases, el
 * `Number()` de los `onChange` y el orden de los dos `select` son idénticos.
 */
export function PeriodSelector({
  mes,
  anio,
  onChangeMes,
  onChangeAnio,
}: {
  mes: number
  anio: number
  onChangeMes: (m: number) => void
  onChangeAnio: (y: number) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <Select size="sm" className="w-auto" value={mes} onChange={(e) => onChangeMes(Number(e.target.value))}>
        {MESES_LARGOS.map((label, i) => (
          <option key={i + 1} value={i + 1}>
            {label}
          </option>
        ))}
      </Select>
      <Select size="sm" className="w-auto" value={anio} onChange={(e) => onChangeAnio(Number(e.target.value))}>
        {ANIOS.map((y) => (
          <option key={y} value={y}>
            {y}
          </option>
        ))}
      </Select>
    </div>
  )
}
