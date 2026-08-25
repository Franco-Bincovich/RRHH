"use client"

import { Pencil, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Objetivo } from "@/types/objetivo"

import {
  COLUMNAS, ESTADO_ESTILO, ESTADO_LABEL, PRIORIDAD_ESTILO, PRIORIDAD_LABEL,
} from "./_grillaObjetivos"
import { aplanar, formatDate, isOverdue } from "./_objetivosFilas"

interface Props {
  objetivos: Objetivo[]
  loading: boolean
  /**
   * Raíces del filtro entero, según el backend. El pie de la tabla lo lee de acá y NUNCA de
   * `objetivos.length`: hoy coinciden porque este listado no pagina, y el día que pagine
   * `length` es el tamaño de la página.
   *
   * ⚠️ El VACÍO sí se deriva de `objetivos`, y es correcto: si la página no trajo nada, no hay
   * nada que dibujar. Son dos preguntas distintas — "¿cuántos hay?" la contesta el backend,
   * "¿qué dibujo ahora?" lo contesta lo que llegó.
   */
  total: number
  showEmpresa: boolean
  canWrite: boolean
  onEdit: (obj: Objetivo) => void
  onDelete: (objetivo: Objetivo) => void
  deletingId: string | null
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` sin permiso. */
  accionVacio?: ReactNode
}

const ACCION_CLASS =
  "flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50"

/**
 * La vista Lista del tablero de objetivos. Dueña de su carga y de su vacío; el ERROR se queda en
 * `ObjetivosVistas`, que lo comparte con la vista Tablero.
 *
 * 🔴 EL PIE NO ES UNA `<Pagination>` Y NO LE FALTA UNA: **este listado no pagina** —el backend
 * devuelve el árbol entero (`objetivo_repo.find_all`)— así que no hay páginas que recorrer. Lo
 * que el pie dice es cuántas RAÍCES hay, que no es la cantidad de filas: la tabla aplana raíces
 * + subobjetivos y casi siempre muestra más renglones. El contrato del wrapper paginado está
 * escrito en `types/objetivo.ts` y se respeta igual: el número sale de `total`, nunca de
 * `objetivos.length`.
 */
export function ListView({
  objetivos, loading, total, showEmpresa, canWrite, onEdit, onDelete, deletingId,
  chips, onLimpiarTodo, accionVacio,
}: Props) {
  const columnas = COLUMNAS
    .filter((c) => c.clave !== "empresa" || showEmpresa)
    .filter((c) => c.clave !== "acciones" || canWrite)

  return (
    <>
      <Table patron="datos">
        <Encabezado columnas={columnas} />
        {loading ? (
          <FilasEsqueleto columnas={columnas} />
        ) : objetivos.length === 0 ? (
          <TablaVacia
            colSpan={columnas.length}
            chips={chips}
            sustantivo="objetivos"
            claveSujeto="Empresa"
            onLimpiarTodo={onLimpiarTodo}
            accion={accionVacio}
          />
        ) : (
          <TableBody>
            {aplanar(objetivos).map(({ obj, esHijo }) => {
              const atrasado = isOverdue(obj.fecha_entrega, obj.estado)
              return (
                <TableRow key={obj.id} className={esHijo ? "group bg-muted/30" : "group"}>
                  <TableCell className={esHijo ? "pl-8 text-muted-foreground" : "font-medium"}>
                    {esHijo && <span aria-hidden className="mr-1.5">↳</span>}
                    {obj.titulo}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {obj.responsables.length > 0
                      ? obj.responsables.map((r) => r.nombre ?? "—").join(", ")
                      : obj.responsable_nombre ?? "—"}
                  </TableCell>
                  <TableCell>
                    {/* El estilo sale de `_grillaObjetivos`: "Media" dejó de pintarse con el color
                        de la marca — ver el 🔴 de ese archivo. */}
                    <Badge variant="outline" className={PRIORIDAD_ESTILO[obj.prioridad]}>
                      {PRIORIDAD_LABEL[obj.prioridad]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {/* Tres estados, NO un porcentaje (§7): la etiqueta dice en cuál está y nada más. */}
                    <Badge variant="outline" className={ESTADO_ESTILO[obj.estado]}>
                      {ESTADO_LABEL[obj.estado]}
                    </Badge>
                  </TableCell>
                  {showEmpresa && <TableCell className="text-muted-foreground">{obj.empresa_nombre ?? "—"}</TableCell>}
                  <TableCell className={atrasado ? "font-semibold text-destructive tabular-nums" : "text-muted-foreground tabular-nums"}>
                    {formatDate(obj.fecha_entrega)}{atrasado ? " ⚠" : ""}
                  </TableCell>
                  {canWrite && (
                    <TableCell className="text-right">
                      {/* 🔴 SIEMPRE VISIBLES, sólo cambian de color al apuntar (§3). */}
                      <div className="flex justify-end gap-1">
                        <button type="button" onClick={() => onEdit(obj)} aria-label={`Editar ${obj.titulo}`}
                          className={`${ACCION_CLASS} group-hover:text-primary`}>
                          <Pencil className="size-4" aria-hidden="true" />
                        </button>
                        <button type="button" onClick={() => onDelete(obj)} disabled={deletingId === obj.id}
                          aria-label={`Eliminar ${obj.titulo}`} className={`${ACCION_CLASS} group-hover:text-destructive`}>
                          <Trash2 className="size-4" aria-hidden="true" />
                        </button>
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              )
            })}
          </TableBody>
        )}
      </Table>

      {/* 🔴 EL PIE CUENTA CON `total`, NO CON LO QUE DIBUJÓ LA TABLA. Y el número de arriba no es
          el de filas: la tabla aplana raíces + subobjetivos, así que casi siempre muestra MÁS
          renglones que objetivos principales hay. Decir "N filas" acá sería un tercer número
          distinto para la misma pregunta. */}
      {!loading && objetivos.length > 0 && (
        <p className="mt-3 text-xs text-muted-foreground tabular-nums">
          {total} {total === 1 ? "objetivo principal" : "objetivos principales"}
          {total > objetivos.length && ` · se muestran ${objetivos.length}`}
        </p>
      )}
    </>
  )
}
