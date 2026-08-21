/**
 * Tabla de la vista "lista" de vacaciones, presentacional. Sin lógica de negocio ni fetch.
 *
 * 🔴 AHORA ES DUEÑA DE SUS TRES ESTADOS (carga, error, vacío) y antes no lo era: los tenía la
 * página porque se compartían con la vista "mapa". El patrón del bloque B los necesita ACÁ —el
 * vacío es una fila con `colSpan` que conserva el encabezado, y para eso tiene que estar adentro
 * de la `<Table>`—. La vista mapa se quedó con los suyos en `VacacionesVistaMapa`, que es un
 * calendario y no tiene encabezado de columnas que conservar.
 *
 * Las piezas del patrón salen enteras de los compartidos (`patron="datos"`, `Encabezado`,
 * `FilasEsqueleto`, `TablaVacia`, `ErrorState`): acá no hay una sola clase de las del patrón.
 */
import { Paperclip } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { SolicitudVacaciones } from "@/types/vacaciones"

import { COLUMNAS, ESTADO_ESTILO, ESTADO_LABEL } from "./_grillaVacaciones"

// Null-safe aunque hoy fecha_desde/fecha_hasta sean NOT NULL en la DB: si alguna vez llegara
// un null, `s.split` tumbaría la tabla entera. Mismo molde que AsignacionesCapTable.
function formatFecha(s: string | null): string {
  if (!s) return "—"
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y}`
}

interface VacacionesTableProps {
  items: SolicitudVacaciones[]
  loading: boolean
  error: boolean
  canWrite: boolean
  showEmpresa: boolean
  cancelingId: string | null
  onRetry: () => void
  onCancel: (id: string) => void
  onDocs: (s: SolicitudVacaciones) => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` si no puede escribir. */
  accionVacio?: ReactNode
}

export function VacacionesTable({
  items, loading, error, canWrite, showEmpresa, cancelingId, onRetry, onCancel, onDocs,
  chips, onLimpiarTodo, accionVacio,
}: VacacionesTableProps) {
  const columnas = COLUMNAS.filter((c) => c.clave !== "empresa" || showEmpresa)

  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó, y ofrecer
  // "quitar un filtro" cuando el problema es la red manda a arreglar lo que no está roto.
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
          sustantivo="vacaciones"
          genero="femenino"
          claveSujeto="Empresa"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {items.map((s) => (
            <TableRow key={s.id} className="group">
              <TableCell className="font-medium">{s.empleado_nombre ?? "—"}</TableCell>
              <TableCell className="text-muted-foreground">{s.area_nombre ?? "—"}</TableCell>
              {showEmpresa && <TableCell className="text-muted-foreground">{s.empresa_nombre ?? "—"}</TableCell>}
              <TableCell className="tabular-nums">{formatFecha(s.fecha_desde)}</TableCell>
              <TableCell className="tabular-nums">{formatFecha(s.fecha_hasta)}</TableCell>
              <TableCell className="tabular-nums">{s.dias}</TableCell>
              <TableCell>
                {/* El estilo sale de `_grillaVacaciones`: ninguno de los tres es azul. Ver el 🔴
                    de ese archivo para qué semántica le toca a cada estado. */}
                <Badge variant="outline" className={ESTADO_ESTILO[s.estado]}>{ESTADO_LABEL[s.estado]}</Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-1">
                  {/* Siempre visible, solo cambia de color al apuntar: revelar la acción en hover
                      obliga a barrer la tabla con el mouse para saber qué se puede hacer. */}
                  <button
                    type="button"
                    onClick={() => onDocs(s)}
                    aria-label={`Documentos de las vacaciones de ${s.empleado_nombre ?? "el colaborador"}`}
                    className="flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors group-hover:text-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                  >
                    <Paperclip className="size-4" aria-hidden="true" />
                  </button>
                  {canWrite && s.estado !== "cancelada" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground transition-colors group-hover:text-destructive"
                      disabled={cancelingId === s.id}
                      onClick={() => onCancel(s.id)}
                    >
                      {cancelingId === s.id ? "Cancelando..." : "Cancelar"}
                    </Button>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
