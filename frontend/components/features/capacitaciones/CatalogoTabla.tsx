"use client"

import { Pencil, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Capacitacion } from "@/types/capacitacion"

import { ACTIVO_ESTILO, COLUMNAS_CATALOGO, OBLIGATORIA_ESTILO } from "./_grillaCapacitaciones"

/**
 * Los cuatro estados de render del catálogo de cursos: cargando, error, vacío y la tabla.
 *
 * Extraído de `CatalogoTab.tsx` (159/150) para poder sumarle el import por Excel. El corte deja
 * el módulo SIMÉTRICO con su hermano, que ya tenía este reparto: `AsignacionesTab` (96,
 * orquestador) + `AsignacionesCapTable` (134, presentacional). El catálogo era el único de los
 * dos tabs que hacía las dos cosas en un archivo.
 *
 * Presentacional puro: sin estado, sin fetch. Los cuatro estados viven juntos y no en el
 * orquestador a propósito — son excluyentes entre sí y decidirlos en dos archivos distintos es
 * cómo aparece la pantalla que muestra el vacío mientras carga.
 */
interface Props {
  capacitaciones: Capacitacion[]
  loading: boolean
  error: boolean
  onReintentar: () => void
  canWrite: boolean
  /** `null` = ninguna borrándose. Deshabilita solo la fila en curso. */
  deletingId: string | null
  onEditar: (c: Capacitacion) => void
  onEliminar: (id: string) => void
  /** El modo consolidado agrega la columna de empresa: un mismo curso puede existir en varias. */
  mostrarEmpresa: boolean
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` sin permiso. */
  accionVacio?: ReactNode
}

const ACCION_CLASS =
  "flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50"

export function CatalogoTabla({
  capacitaciones, loading, error, onReintentar, canWrite, deletingId,
  onEditar, onEliminar, mostrarEmpresa, chips, onLimpiarTodo, accionVacio,
}: Props) {
  const columnas = COLUMNAS_CATALOGO
    .filter((c) => c.clave !== "empresa" || mostrarEmpresa)
    .filter((c) => c.clave !== "acciones" || canWrite)

  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó.
  if (error) return <ErrorState action={onReintentar} />

  return (
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : capacitaciones.length === 0 ? (
        /* Sin `claveSujeto`: el sujeto sería la EMPRESA, y acá la empresa es un chip más — el
           curso pertenece al catálogo, no a una persona. La frase arranca impersonal. */
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="formaciones"
          genero="femenino"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
      <TableBody>
        {capacitaciones.map((c) => (
          <TableRow key={c.id} className="group">
            <TableCell className="font-medium">{c.nombre}</TableCell>
            <TableCell className="text-muted-foreground">{c.categoria ?? "—"}</TableCell>
            <TableCell className="text-muted-foreground">{c.duracion_horas != null ? `${c.duracion_horas} hs` : "—"}</TableCell>
            {mostrarEmpresa && <TableCell className="text-muted-foreground">{c.empresa_nombre ?? "—"}</TableCell>}
            <TableCell>
              {/* El estilo sale de `_grillaCapacitaciones`: ninguno de los dos es azul, y
                  "Obligatoria" va con el par de ATENCIÓN — es una condición que genera trabajo,
                  no un logro. Ver el 🔴 de ese archivo. */}
              <Badge variant="outline" className={c.obligatoria ? OBLIGATORIA_ESTILO.si : OBLIGATORIA_ESTILO.no}>
                {c.obligatoria ? "Sí" : "No"}
              </Badge>
            </TableCell>
            <TableCell>
              <Badge variant="outline" className={c.activo ? ACTIVO_ESTILO.activo : ACTIVO_ESTILO.inactivo}>
                {c.activo ? "Activo" : "Inactivo"}
              </Badge>
            </TableCell>
            {canWrite && (
              <TableCell className="text-right">
                {/* 🔴 SIEMPRE VISIBLES, sólo cambian de color al apuntar (§3). El rojo del
                    borrado aparece recién con el mouse en la fila. */}
                <div className="flex justify-end gap-1">
                  <button type="button" onClick={() => onEditar(c)} aria-label={`Editar ${c.nombre}`}
                    className={`${ACCION_CLASS} group-hover:text-primary`}>
                    <Pencil className="size-4" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => onEliminar(c.id)} disabled={deletingId === c.id}
                    aria-label={`Eliminar ${c.nombre}`} className={`${ACCION_CLASS} group-hover:text-destructive`}>
                    <Trash2 className="size-4" aria-hidden="true" />
                  </button>
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
