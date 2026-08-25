"use client"

/**
 * Tabla del catálogo de ítems de inventario: presentacional. Dueña de los cuatro estados del
 * listado (cargando / error / vacío / datos) y sin saber nada de filtros ni de fetch.
 *
 * Molde: AsignacionesInvTable.tsx, la tabla de la pestaña hermana.
 *
 * `deletingId` entra por prop y no es estado propio: el borrado lo dispara y lo reintenta el
 * orquestador, que es quien tiene el service y el toast de error.
 */
import { History, Pencil, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { InventarioItem } from "@/types/inventario"

import { COLUMNAS_ITEMS, ESTADO_ITEM_ESTILO, ESTADO_ITEM_LABEL } from "./_grillaInventario"

function formatDate(s: string) {
  const [y, m, d] = s.split("-"); return `${d}/${m}/${y}`
}

interface ItemsInvTableProps {
  items: InventarioItem[]
  loading: boolean
  error: boolean
  canWrite: boolean
  mostrarEmpresa: boolean
  deletingId: string | null
  onReload: () => void
  onHistorial: (item: InventarioItem) => void
  onEditar: (item: InventarioItem) => void
  onEliminar: (item: InventarioItem) => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` sin permiso. */
  accionVacio?: ReactNode
}

const ACCION_CLASS =
  "flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50"

export function ItemsInvTable({
  items, loading, error, canWrite, mostrarEmpresa, deletingId,
  onReload, onHistorial, onEditar, onEliminar, chips, onLimpiarTodo, accionVacio,
}: ItemsInvTableProps) {
  const columnas = COLUMNAS_ITEMS.filter((c) => c.clave !== "empresa" || mostrarEmpresa)

  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó.
  if (error) return <ErrorState action={onReload} />

  return (
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : items.length === 0 ? (
        /* Sin `claveSujeto`: el sujeto de la frase sería la EMPRESA, y acá la empresa es un chip
           más —no el sujeto de "X no tiene ítems"—, porque el ítem pertenece al inventario y no a
           una persona. La frase arranca impersonal: "No hay ítems con…". */
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="ítems"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id} className="group">
              <TableCell className="font-medium">{item.nombre}</TableCell>
              <TableCell className="text-muted-foreground">{item.tipo}</TableCell>
              <TableCell className="text-muted-foreground">{item.numero_serie ?? "—"}</TableCell>
              <TableCell>
                {/* El estilo sale de `_grillaInventario`: ninguno de los cuatro es azul. */}
                <Badge variant="outline" className={ESTADO_ITEM_ESTILO[item.estado] ?? ""}>
                  {ESTADO_ITEM_LABEL[item.estado] ?? item.estado}
                </Badge>
              </TableCell>
              {mostrarEmpresa && <TableCell className="text-muted-foreground">{item.empresa_nombre ?? "—"}</TableCell>}
              <TableCell className="text-muted-foreground">{item.asignado_a ?? "—"}</TableCell>
              <TableCell className="text-muted-foreground tabular-nums">{formatDate(item.fecha_alta)}</TableCell>
              <TableCell>
                {/* 🔴 SIEMPRE VISIBLES, sólo cambian de color al apuntar (§3). El historial va
                    incluso sin permiso de escritura: es una LECTURA, y la sección la tiene todo
                    el que llega a esta pestaña. */}
                <div className="flex items-center gap-1">
                  <button type="button" onClick={() => onHistorial(item)} aria-label={`Historial de ${item.nombre}`}
                    className={`${ACCION_CLASS} group-hover:text-primary`}>
                    <History className="size-4" aria-hidden="true" />
                  </button>
                  {canWrite && (
                    <>
                      <button type="button" onClick={() => onEditar(item)} aria-label={`Editar ${item.nombre}`}
                        className={`${ACCION_CLASS} group-hover:text-primary`}>
                        <Pencil className="size-4" aria-hidden="true" />
                      </button>
                      <button type="button" onClick={() => onEliminar(item)} disabled={deletingId === item.id}
                        aria-label={`Eliminar ${item.nombre}`}
                        className={`${ACCION_CLASS} group-hover:text-destructive`}>
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
