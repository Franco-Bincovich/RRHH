/**
 * Tabla de bajas, presentacional. Dueña de los estados de carga/error/vacío. Sin fetch ni lógica
 * de negocio: la página le pasa datos y el handler de navegación a la ficha.
 *
 * Las piezas del patrón salen enteras de los compartidos (`patron="datos"`, `Encabezado`,
 * `FilasEsqueleto`, `TablaVacia`, `ErrorState`): acá no hay una sola clase de las del patrón.
 */
import { ChevronRight } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { formatFecha } from "@/components/features/shared/fechas"
import type { Empleado } from "@/types/empleado"

import { COLUMNAS, antiguedadAlEgreso } from "./_bajas"

interface Props {
  items: Empleado[]
  loading: boolean
  error: boolean
  showEmpresa: boolean
  onRetry: () => void
  onRowClick: (id: string) => void
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  accionVacio?: ReactNode
}

export function BajasTable({
  items, loading, error, showEmpresa, onRetry, onRowClick, chips, onLimpiarTodo, accionVacio,
}: Props) {
  const columnas = COLUMNAS.filter((c) => c.clave !== "empresa" || showEmpresa)

  if (error) return <ErrorState action={onRetry} />

  return (
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : items.length === 0 ? (
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="bajas"
          claveSujeto="Empresa"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {items.map((emp) => (
            <TableRow key={emp.id} className="group cursor-pointer" onClick={() => onRowClick(emp.id)}>
              <TableCell className="font-medium">{emp.nombre} {emp.apellido}</TableCell>
              {showEmpresa && <TableCell className="text-muted-foreground">{emp.empresa_nombre ?? "—"}</TableCell>}
              {/*
               * 🔴 UNA FILA SIN `fecha_egreso` SALE PRIMERA Y ESO ESTÁ BIEN. El orden es
               * `fecha_egreso DESC` y postgrest no puede expresar `NULLS LAST` (su `order` solo
               * tiene `nullsfirst`), así que los nulos quedan arriba — está pineado con un test
               * del backend, en `_empleado_orden.ordenado`. NO se reordena acá: el listado
               * pagina, y ordenar el cliente ordenaría solo la página que llegó. Lo que la
               * celda muestra es el guion de `formatFecha`, que es la señal de que a esa baja le
               * falta el dato.
               */}
              <TableCell className="tabular-nums">{formatFecha(emp.fecha_egreso)}</TableCell>
              {/*
               * 🔴 EL MOTIVO VACÍO SE MUESTRA VACÍO. Una baja que vino del import de nómina sin
               * la columna `Motivo Baja`, o sin instancia de offboarding detrás, no tiene motivo
               * — y escribir ahí "Sin especificar" convertiría "no sabemos por qué se fue" en un
               * motivo cargado, que es justo lo que un listado de bajas no puede hacer. (El
               * reporte de movimientos SÍ lo rellena, porque agrupa y necesita un cubo donde
               * poner esas filas; acá cada fila es una persona.)
               */}
              <TableCell className="text-muted-foreground">{emp.motivo_baja || ""}</TableCell>
              <TableCell className="text-muted-foreground">{antiguedadAlEgreso(emp)}</TableCell>
              <TableCell>
                {/* Siempre visible, solo cambia de color al apuntar: revelar la acción en hover
                    obliga a barrer la tabla con el mouse para saber qué se puede hacer. */}
                <button
                  type="button"
                  aria-label={`Ver ficha de ${emp.nombre} ${emp.apellido}`}
                  onClick={(e) => { e.stopPropagation(); onRowClick(emp.id) }}
                  className="flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors group-hover:text-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                >
                  <ChevronRight className="size-4" aria-hidden="true" />
                </button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
