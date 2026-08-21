/**
 * Tabla de próximos ingresos, presentacional. Dueña de los estados de carga/error/vacío. Sin
 * fetch ni lógica de negocio: la página le pasa datos, el handler de navegación y el de activar.
 *
 * Los cinco patrones del bloque B salen enteros de las piezas compartidas —`patron="datos"` del
 * primitivo de tabla, `Encabezado`/`FilasEsqueleto` de `grillaTabla`, `TablaVacia`, `ErrorState`—;
 * acá no hay una sola clase de las del patrón.
 */
import { UserCheck } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Button } from "@/components/ui/button"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { diasHasta, formatFecha } from "@/components/features/shared/fechas"
import type { PersonaActivable } from "@/components/features/empleados/useActivarEmpleado"
import type { Empleado } from "@/types/empleado"

import { COLUMNAS, textoFaltan } from "./_proximosIngresos"

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
  /** `undefined` si el rol no puede escribir: entonces no se dibuja la columna de acciones. */
  onActivar?: (empleado: PersonaActivable) => void
  /** El id de la fila que se está confirmando ahora mismo, o `null`. */
  activandoId: string | null
}

export function ProximosIngresosTable({
  items, loading, error, showEmpresa, onRetry, onRowClick, chips, onLimpiarTodo, accionVacio,
  onActivar, activandoId,
}: Props) {
  const columnas = COLUMNAS.filter(
    (c) => (c.clave !== "empresa" || showEmpresa) && (c.clave !== "acciones" || onActivar),
  )

  if (error) return <ErrorState action={onRetry} />

  return (
    // Una sola <Table> para los tres estados: el encabezado se renderiza SIEMPRE, así la
    // pantalla no cambia de forma entre la carga, el vacío y los datos.
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : items.length === 0 ? (
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="próximos ingresos"
          claveSujeto="Empresa"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {items.map((emp) => {
            const faltan = textoFaltan(diasHasta(emp.fecha_ingreso))
            return (
              <TableRow key={emp.id} className="group cursor-pointer" onClick={() => onRowClick(emp.id)}>
                <TableCell className="font-medium">{emp.nombre} {emp.apellido}</TableCell>
                {showEmpresa && <TableCell className="text-muted-foreground">{emp.empresa_nombre ?? "—"}</TableCell>}
                <TableCell className="text-muted-foreground">{emp.area_nombre ?? "—"}</TableCell>
                <TableCell className="tabular-nums">{formatFecha(emp.fecha_ingreso)}</TableCell>
                <TableCell className={faltan.destacado ? "font-medium text-warning" : "text-muted-foreground"}>
                  {faltan.texto}
                </TableCell>
                {onActivar && (
                  <TableCell>
                    {/*
                     * 🔴 EL BOTÓN NO SE DESHABILITA POR FECHA. Se podría —`diasHasta` ya está
                     * calculado dos líneas arriba— y sería peor: un botón muerto no dice por qué
                     * lo está. El backend rechaza con 400 `INGRESO_AUN_NO_OCURRIO`, y ese mensaje
                     * trae la fecha que falta Y la salida ("corregí la fecha en el legajo y
                     * después activala"), que es justamente el caso que hay que resolver cuando
                     * alguien entró antes de lo previsto. El único `disabled` es mientras la
                     * llamada está en vuelo, para no mandarla dos veces.
                     *
                     * `stopPropagation` porque la fila entera navega a la ficha: sin él, apretar
                     * el botón además cambiaría de pantalla.
                     */}
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={activandoId === emp.id}
                      onClick={(e) => { e.stopPropagation(); onActivar(emp) }}
                    >
                      <UserCheck className="size-3.5" aria-hidden="true" />
                      {activandoId === emp.id ? "Confirmando..." : "Confirmar ingreso"}
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            )
          })}
        </TableBody>
      )}
    </Table>
  )
}
