/**
 * Tabla de ausencias, presentacional. Dueña de los estados de carga/error/vacío y del
 * formato de fecha. Sin lógica de negocio ni fetch: la página le pasa datos y callbacks.
 *
 * Las piezas del patrón "Tabla con paginación" (`docs/SISTEMA-DE-DISENO.md` §3) salen enteras de
 * los compartidos (`patron="datos"`, `Encabezado`, `FilasEsqueleto`, `TablaVacia`, `ErrorState`):
 * acá no hay una sola clase de las del patrón. Molde: `BajasTable` / `EmpleadosTable`.
 */
import { Paperclip, Pencil, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Ausencia } from "@/types/ausencias"

import { COLUMNAS } from "./_grillaAusencias"

interface AusenciasTableProps {
  items: Ausencia[]
  loading: boolean
  error: boolean
  showEmpresa: boolean
  canWrite: boolean
  deletingId: string | null
  onRetry: () => void
  onEdit: (a: Ausencia) => void
  onDelete: (id: string) => void
  onDocs: (a: Ausencia) => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` si no puede escribir. */
  accionVacio?: ReactNode
}

function formatFecha(s: string): string {
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y}`
}

/*
 * 🔴 LAS ACCIONES ESTÁN SIEMPRE VISIBLES Y SOLO CAMBIAN DE COLOR AL APUNTAR (§3). Revelarlas en
 * hover obliga a barrer la tabla con el mouse para saber qué se puede hacer con cada fila; acá los
 * tres íconos se ven desde el primer render y lo único que hace el hover de la fila es subirles el
 * contraste. El rojo del borrado también aparece recién al apuntar: en reposo, diez filas con un
 * ícono rojo cada una leen como diez errores.
 */
const ACCION_CLASS =
  "flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50"

export function AusenciasTable({
  items, loading, error, showEmpresa, canWrite, deletingId, onRetry, onEdit, onDelete, onDocs,
  chips, onLimpiarTodo, accionVacio,
}: AusenciasTableProps) {
  const columnas = COLUMNAS.filter((c) => c.clave !== "empresa" || showEmpresa)

  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó, y ofrecer
  // "quitar un filtro" cuando el problema es la red manda a arreglar lo que no está roto.
  if (error) return <ErrorState action={onRetry} />

  return (
    /*
     * 🔴 UNA SOLA `<Table>` PARA LOS TRES ESTADOS — carga, vacío y datos. El encabezado se
     * renderiza SIEMPRE (§3), así que la pantalla no cambia de forma entre uno y otro.
     */
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : items.length === 0 ? (
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="ausencias"
          genero="femenino"
          claveSujeto="Empresa"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {items.map((a) => (
            <TableRow key={a.id} className="group">
              <TableCell className="font-medium">{a.empleado_nombre ?? "—"}</TableCell>
              <TableCell className="text-muted-foreground">{a.area_nombre ?? "—"}</TableCell>
              {showEmpresa && <TableCell className="text-muted-foreground">{a.empresa_nombre ?? "—"}</TableCell>}
              <TableCell>{a.tipo_nombre ?? "—"}</TableCell>
              <TableCell className="tabular-nums">{formatFecha(a.fecha_desde)}</TableCell>
              <TableCell className="tabular-nums">{formatFecha(a.fecha_hasta)}</TableCell>
              <TableCell className="tabular-nums">{a.dias}</TableCell>
              <TableCell>
                {/* Ninguno de los dos es azul: el relleno `--primary` está reservado al chip de
                    filtro (§3). "No justificada" va con el par de warning porque es lo que pide
                    una revisión, no un error del sistema. */}
                <Badge
                  variant="outline"
                  className={a.justificada
                    ? "bg-success-wash text-success border-success-line"
                    : "bg-warning-wash text-warning border-warning-line"}
                >
                  {a.justificada ? "Sí" : "No"}
                </Badge>
              </TableCell>
              <TableCell className="max-w-[200px] truncate text-muted-foreground text-sm">
                {a.motivo ?? "—"}
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-1">
                  <button type="button" onClick={() => onDocs(a)} aria-label={`Documentos de la ausencia de ${a.empleado_nombre ?? "el colaborador"}`} className={`${ACCION_CLASS} group-hover:text-primary`}>
                    <Paperclip className="size-4" aria-hidden="true" />
                  </button>
                  {canWrite && (
                    <>
                      <button type="button" onClick={() => onEdit(a)} aria-label={`Editar la ausencia de ${a.empleado_nombre ?? "el colaborador"}`} className={`${ACCION_CLASS} group-hover:text-primary`}>
                        <Pencil className="size-4" aria-hidden="true" />
                      </button>
                      <button type="button" onClick={() => onDelete(a.id)} disabled={deletingId === a.id} aria-label={`Eliminar la ausencia de ${a.empleado_nombre ?? "el colaborador"}`} className={`${ACCION_CLASS} group-hover:text-destructive`}>
                        <Trash2 className="size-4" aria-hidden="true" />
                      </button>
                    </>
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
