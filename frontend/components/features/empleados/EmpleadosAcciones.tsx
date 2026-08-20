/**
 * Las acciones del encabezado de /empleados: exportar, importar nómina y alta.
 *
 * Salió de `page.tsx` al aplicarle los patrones del sistema de diseño (la página quedaba en 160
 * líneas contra el límite de 150). El corte es por responsabilidad y no por tamaño: acá está lo
 * que la pantalla OFRECE HACER, y en la página lo que la pantalla MUESTRA — datos, filtros, tabla
 * y pie. Ninguna de las tres acciones necesita el estado del listado.
 */
import { Plus, Upload } from "lucide-react"

import { ExportMenu } from "@/components/features/export/ExportMenu"
import { Button } from "@/components/ui/button"
import { exportarEmpleados, type EmpleadosFiltros } from "@/services/empleados"
import type { FormatoExport } from "@/services/api"

interface EmpleadosAccionesProps {
  /** Los MISMOS filtros que el listado. Ver el 🔴 de `page.tsx`: un solo objeto para los dos. */
  filtros: EmpleadosFiltros
  /** El export se ofrece sólo cuando hay algo que exportar (sin filas el archivo saldría vacío). */
  mostrarExport: boolean
  canWrite: boolean
  onImportar: () => void
  onNuevo: () => void
}

export function EmpleadosAcciones({ filtros, mostrarExport, canWrite, onImportar, onNuevo }: EmpleadosAccionesProps) {
  return (
    <div className="flex items-center gap-2">
      {mostrarExport && (
        <ExportMenu onExport={(f: FormatoExport) => exportarEmpleados({ formato: f, ...filtros })} />
      )}
      {canWrite && (
        <>
          <Button variant="outline" className="min-h-11 gap-1.5" onClick={onImportar}>
            <Upload className="size-4" />
            Importar nómina
          </Button>
          <Button className="min-h-11" onClick={onNuevo}>
            <Plus />
            Nuevo empleado
          </Button>
        </>
      )}
    </div>
  )
}
