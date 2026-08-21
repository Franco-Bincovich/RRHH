"use client"

import { ANIOS, MESES_LARGOS } from "@/components/features/costos/formatos"
import { Select } from "@/components/ui/select"

/**
 * Selector de mes y año. Presentacional y controlado: no tiene estado propio ni fetchea.
 *
 * Movido VERBATIM desde `costos/page.tsx` al partirla (624 → orquestador), y de ahí a `shared/`
 * el 21/8/2026 al aparecer el SEGUNDO consumidor: `/horas-por-cliente`, que tenía dos `<Input
 * type="number">` para lo mismo — o sea, había que TIPEAR "3" para ver marzo, y nada impedía
 * escribir 13. Dos controles con afordancias distintas para el mismo dato es exactamente lo que
 * este primitivo evita; `features/costos/PeriodSelector.tsx` lo RE-EXPORTA, así que ese import
 * sigue funcionando igual.
 *
 * 🔴 ESTE CONTROL NO ES UN CHIP, Y NO PUEDE SERLO. En las dos pantallas que lo usan, `mes` y
 * `anio` son `Query(...)` **sin default** en el backend: un chip promete que el filtro se puede
 * quitar —su ✕ llama al `onChange` con vacío— y acá quitarlo no deja la pantalla sin filtrar,
 * deja la consulta rota. Por eso vive en el encabezado y no en `<FiltersBar>`.
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
