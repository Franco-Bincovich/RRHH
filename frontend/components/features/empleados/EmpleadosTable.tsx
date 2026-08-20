/**
 * Tabla de empleados, presentacional. Dueña de los estados de carga/error/vacío. Sin fetch
 * ni lógica de negocio: la página le pasa datos y el handler de navegación a la ficha.
 *
 * Es la PANTALLA PILOTO del patrón "Tabla con paginación" de `docs/SISTEMA-DE-DISENO.md` §3:
 * la densidad, el encabezado, el hover y la marca de 3px salen enteros de `patron="datos"` del
 * primitivo (`components/ui/table.tsx`) — acá no hay una sola clase de las del patrón.
 */
import { ChevronRight } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Empleado } from "@/types/empleado"

import { ESTADO_ESTILO, etiquetaEstado } from "./_estadoEmpleado"
import { COLUMNAS, Encabezado, FilasEsqueleto } from "./_grillaEmpleados"

interface EmpleadosTableProps {
  items: Empleado[]
  loading: boolean
  error: boolean
  showEmpresa: boolean
  onRetry: () => void
  onRowClick: (id: string) => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` si no puede escribir. */
  accionVacio?: ReactNode
}

export function EmpleadosTable({
  items, loading, error, showEmpresa, onRetry, onRowClick, chips, onLimpiarTodo, accionVacio,
}: EmpleadosTableProps) {
  const columnas = COLUMNAS.filter((c) => c.clave !== "empresa" || showEmpresa)

  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó, y ofrecer
  // "quitar un filtro" cuando el problema es la red manda a arreglar lo que no está roto.
  if (error) return <ErrorState action={onRetry} />

  return (
    /*
     * 🔴 UNA SOLA `<Table>` PARA LOS TRES ESTADOS — carga, vacío y datos. El encabezado se
     * renderiza SIEMPRE (§3), así que la pantalla no cambia de forma entre uno y otro: al llegar
     * los datos, las columnas ya están en su lugar y con su ancho.
     */
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : items.length === 0 ? (
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="colaboradores"
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
              <TableCell className="text-muted-foreground">{emp.area_nombre ?? "—"}</TableCell>
              <TableCell>{(emp.roles ?? []).join(", ") || emp.cargo || "—"}</TableCell>
              <TableCell className="capitalize">{emp.modalidad_trabajo}</TableCell>
              <TableCell>
                <Badge variant="outline" className={ESTADO_ESTILO[emp.estado] ?? ""}>
                  {etiquetaEstado(emp.estado)}
                </Badge>
              </TableCell>
              <TableCell>
                {/*
                 * 🔴 SIEMPRE VISIBLE, solo cambia de color al apuntar (§3). Revelar la acción en
                 * hover obliga a barrer la tabla con el mouse para saber qué se puede hacer.
                 * `stopPropagation` porque la fila entera ya navega: sin él se dispararían las dos
                 * navegaciones al mismo destino.
                 */}
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
