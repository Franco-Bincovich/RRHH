"use client"

import { Pencil, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Cliente } from "@/types/cliente"

import { COLUMNAS, ESTADO_ESTILO } from "./_grillaClientes"

interface Props {
  clientes: Cliente[]
  loading: boolean
  error: string | null
  canWrite: boolean
  onRetry: () => void
  onEdit: (c: Cliente) => void
  onDelete: (c: Cliente) => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` si no puede escribir. */
  accionVacio?: ReactNode
}

const ACCION_CLASS =
  "flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

/**
 * Tabla del catálogo de clientes. PRESENTACIONAL: sin fetch ni lógica de negocio.
 *
 * 🔴 AHORA ES DUEÑA DE SUS TRES ESTADOS (carga, error, vacío) y antes no lo era: los tenía la
 * página, con `return` tempranos que **reemplazaban la pantalla entera** durante la carga. El
 * patrón del bloque B los necesita acá: el vacío es una fila con `colSpan`, y para eso tiene que
 * estar adentro de la `<Table>`.
 *
 * ⚠️ Los botones de escritura se OMITEN cuando `canWrite` es false, no se deshabilitan. Un
 * `disabled` sobre el `Button` de shadcn no se puede afirmar en un test —el markup trae la
 * clase `disabled:...` de Tailwind SIEMPRE, así que `not.toContain("disabled")` pasa con el
 * guard borrado— y además un botón muerto invita a clickearlo. Ver ClientesTabla.test.tsx.
 * Por eso la COLUMNA entera de acciones también se filtra: una columna vacía con su encabezado
 * es una promesa que la pantalla no cumple.
 */
export function ClientesTabla({
  clientes, loading, error, canWrite, onRetry, onEdit, onDelete, chips, onLimpiarTodo, accionVacio,
}: Props) {
  const columnas = COLUMNAS.filter((c) => c.clave !== "acciones" || canWrite)

  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó, y ofrecer
  // "quitar un filtro" cuando el problema es la red manda a arreglar lo que no está roto.
  if (error) return <ErrorState description={error} action={onRetry} />

  return (
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : clientes.length === 0 ? (
        /* Sin `claveSujeto`: el sujeto de la frase sería la EMPRESA, y este catálogo es GLOBAL —
           no pertenece a ninguna. La frase arranca impersonal: "No hay clientes con…". */
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="clientes"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {clientes.map((c) => (
            <TableRow key={c.id} className="group">
              <TableCell className="font-medium">{c.nombre}</TableCell>
              <TableCell>
                {/* El estilo sale de `_grillaClientes`: ninguno de los dos es azul. Ver el 🔴 de
                    ese archivo para qué semántica le toca a cada estado. */}
                <Badge variant="outline" className={c.activo ? ESTADO_ESTILO.activo : ESTADO_ESTILO.baja}>
                  {c.activo ? "Activo" : "Dado de baja"}
                </Badge>
              </TableCell>
              {canWrite && (
                <TableCell className="text-right">
                  {/* 🔴 SIEMPRE VISIBLES, sólo cambian de color al apuntar (§3). El rojo del
                      borrado aparece recién al apuntar la fila: en reposo, una columna de íconos
                      rojos se lee como una lista de errores. */}
                  <div className="flex justify-end gap-1">
                    <button type="button" aria-label={`Editar ${c.nombre}`} onClick={() => onEdit(c)}
                      className={`${ACCION_CLASS} group-hover:text-primary`}>
                      <Pencil className="size-4" aria-hidden="true" />
                    </button>
                    {c.activo && (
                      <button type="button" aria-label={`Dar de baja ${c.nombre}`} onClick={() => onDelete(c)}
                        className={`${ACCION_CLASS} group-hover:text-destructive`}>
                        <Trash2 className="size-4" aria-hidden="true" />
                      </button>
                    )}
                  </div>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
