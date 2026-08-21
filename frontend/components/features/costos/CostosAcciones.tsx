"use client"

import { FileSpreadsheet, Upload } from "lucide-react"

import { Button } from "@/components/ui/button"
import { PeriodSelector } from "@/components/features/costos/PeriodSelector"

/**
 * Las acciones del encabezado de `/costos`: el selector de período y los dos botones de carga.
 *
 * Salió de `costos/page.tsx` al migrar la pantalla al patrón del bloque B: el archivo pasaba de
 * las 150 líneas al sumarle la explicación de por qué acá el período NO va en un panel de chips.
 *
 * 🔴 EL PERÍODO ES UN FILTRO Y ESTÁ EN EL ENCABEZADO, no en un `<FiltersBar panel>`, y eso es lo
 * que hay que entender antes de "unificarlo": `mes` y `anio` son `Query(...)` **sin default** en
 * los tres endpoints de costos. Un chip promete que el filtro se puede quitar —su ✕ llama al
 * `onChange` con vacío— y acá quitarlo no deja la pantalla sin filtrar, deja la consulta rota.
 * Mismo criterio que `/horas-por-cliente`.
 */
export function CostosAcciones({
  mes, anio, onChangeMes, onChangeAnio, canWrite, onImportar, onCargar,
}: {
  mes: number
  anio: number
  onChangeMes: (m: number) => void
  onChangeAnio: (y: number) => void
  canWrite: boolean
  onImportar: () => void
  onCargar: () => void
}) {
  return (
    <div className="flex items-center gap-2">
      <PeriodSelector mes={mes} anio={anio} onChangeMes={onChangeMes} onChangeAnio={onChangeAnio} />
      {canWrite && (
        <>
          <Button variant="outline" className="min-h-11 gap-1.5" onClick={onImportar}>
            <FileSpreadsheet className="size-4" />
            Importar CSV
          </Button>
          <Button className="min-h-11 gap-1.5" onClick={onCargar}>
            <Upload className="size-4" />
            Cargar nómina
          </Button>
        </>
      )}
    </div>
  )
}
