"use client"

import { Pencil, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Area } from "@/types/area"

import { COLUMNAS } from "./_grillaAreas"

interface Props {
  areas: Area[]
  loading: boolean
  error: boolean
  canWrite: boolean
  onRetry: () => void
  onEdit: (a: Area) => void
  onDelete: (a: Area) => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` si no puede escribir. */
  accionVacio?: ReactNode
}

/**
 * Tabla de áreas. PRESENTACIONAL: sin fetch ni lógica de negocio.
 *
 * 🔴 AHORA ES DUEÑA DE SUS TRES ESTADOS (carga, error, vacío) y antes no lo era: los tenía la
 * página, con `return` tempranos que **reemplazaban la pantalla entera** — durante la carga
 * desaparecían el encabezado, el buscador y el título, y volvían al llegar los datos. El patrón
 * del bloque B necesita los tres acá: el vacío es una fila con `colSpan`, y para eso tiene que
 * estar adentro de la `<Table>`.
 *
 * Las piezas del patrón salen enteras de los compartidos (`patron="datos"`, `Encabezado`,
 * `FilasEsqueleto`, `TablaVacia`, `ErrorState`): acá no hay una sola clase de las del patrón.
 *
 * ⚠️ Los botones de escritura se OMITEN cuando `canWrite` es false, no se deshabilitan: un
 * `disabled` sobre el Button de shadcn no se puede afirmar en un test (la clase `disabled:`
 * viaja siempre) y además un botón muerto invita a clickearlo.
 */
export function AreasTabla({
  areas, loading, error, canWrite, onRetry, onEdit, onDelete, chips, onLimpiarTodo, accionVacio,
}: Props) {
  const columnas = COLUMNAS.filter((c) => c.clave !== "acciones" || canWrite)

  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó, y ofrecer
  // "quitar un filtro" cuando el problema es la red manda a arreglar lo que no está roto.
  if (error) return <ErrorState description="No se pudieron cargar las áreas." action={onRetry} />

  return (
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : areas.length === 0 ? (
        /* Sin `claveSujeto`: el sujeto de la frase sería la EMPRESA y acá la empresa no es un
           chip — la manda el selector del sidebar. La frase arranca impersonal. */
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="áreas"
          genero="femenino"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {areas.map((area) => (
            <TableRow key={area.id} className="group">
              <TableCell className="font-medium">{area.nombre}</TableCell>
              <TableCell className="text-muted-foreground">
                {area.descripcion ?? <span className="italic text-muted-foreground/60">—</span>}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {area.responsable_nombre ?? <span className="italic text-muted-foreground/60">—</span>}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {area.cantidad_empleados}
              </TableCell>
              {canWrite && (
                <TableCell className="text-right">
                  {/* 🔴 SIEMPRE VISIBLES, sólo cambian de color al apuntar (§3). Revelarlas en
                      hover obliga a barrer la tabla con el mouse para saber qué se puede hacer;
                      y el rojo del borrado aparece recién al apuntar la fila, porque veinte
                      íconos rojos en reposo se leen como veinte errores. */}
                  <div className="flex justify-end gap-1">
                    <button type="button" aria-label={`Editar ${area.nombre}`} onClick={() => onEdit(area)}
                      className="flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors group-hover:text-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50">
                      <Pencil className="size-4" aria-hidden="true" />
                    </button>
                    <button type="button" aria-label={`Eliminar ${area.nombre}`} onClick={() => onDelete(area)}
                      className="flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors group-hover:text-destructive hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50">
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
