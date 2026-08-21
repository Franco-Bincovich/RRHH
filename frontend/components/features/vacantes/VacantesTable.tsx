"use client"

import { ChevronRight } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Vacante } from "@/types/vacantes"

import { COLUMNAS, ESTADO_ESTILO, ESTADO_LABEL } from "./_grillaVacantes"

function formatFecha(raw: string | null): string {
  if (!raw) return "—"
  const d = new Date(raw)
  return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

interface VacantesTableProps {
  vacantes: Vacante[]
  loading: boolean
  error: boolean
  /** En modo consolidado se agrega la columna Empresa: sin ella no se sabe de cuál es cada una. */
  mostrarEmpresa: boolean
  onRetry: () => void
  onAbrir: (id: string) => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` si no puede escribir. */
  accionVacio?: ReactNode
}

/**
 * Tabla de vacantes, con la fila entera como link al detalle. Presentacional: sin estado ni fetch.
 *
 * 🔴 AHORA ES DUEÑA DE SUS TRES ESTADOS (carga, error, vacío) y antes no lo era: los tenía la
 * página, con un esqueleto de barras sueltas (`VacantesTableSkeleton`) que no compartía columnas
 * con la tabla y un `<EmptyState>` que la reemplazaba entera. El patrón del bloque B los necesita
 * ACÁ: el vacío es una fila con `colSpan`, y para eso tiene que estar adentro de la `<Table>`.
 *
 * Las piezas del patrón salen enteras de los compartidos (`patron="datos"`, `Encabezado`,
 * `FilasEsqueleto`, `TablaVacia`, `ErrorState`): acá no hay una sola clase de las del patrón.
 */
export function VacantesTable({
  vacantes, loading, error, mostrarEmpresa, onRetry, onAbrir, chips, onLimpiarTodo, accionVacio,
}: VacantesTableProps) {
  const columnas = COLUMNAS.filter((c) => c.clave !== "empresa" || mostrarEmpresa)

  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó, y ofrecer
  // "quitar un filtro" cuando el problema es la red manda a arreglar lo que no está roto.
  if (error) return <ErrorState action={onRetry} />

  return (
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : vacantes.length === 0 ? (
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="vacantes"
          genero="femenino"
          claveSujeto="Empresa"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {vacantes.map((vacante) => (
            <TableRow key={vacante.id} className="group cursor-pointer" onClick={() => onAbrir(vacante.id)}>
              <TableCell className="font-medium">{vacante.titulo}</TableCell>
              {mostrarEmpresa && (
                <TableCell className="text-muted-foreground">{vacante.empresa_nombre ?? "—"}</TableCell>
              )}
              <TableCell className="text-muted-foreground">{vacante.area_nombre ?? "—"}</TableCell>
              <TableCell>
                {/* El estilo sale de `_grillaVacantes`: ninguno de los cuatro es azul. Ver el 🔴
                    de ese archivo para qué semántica le toca a cada estado del embudo. */}
                <Badge variant="outline" className={ESTADO_ESTILO[vacante.estado]}>
                  {ESTADO_LABEL[vacante.estado]}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground tabular-nums">
                {formatFecha(vacante.fecha_apertura ?? vacante.created_at)}
              </TableCell>
              <TableCell>
                {/*
                 * 🔴 SIEMPRE VISIBLE, solo cambia de color al apuntar (§3). Revelar la acción en
                 * hover obliga a barrer la tabla con el mouse para saber qué se puede hacer.
                 * `stopPropagation` porque la fila entera ya navega: sin él se dispararían las
                 * dos navegaciones al mismo destino.
                 */}
                <button
                  type="button"
                  aria-label={`Ver la vacante ${vacante.titulo}`}
                  onClick={(e) => { e.stopPropagation(); onAbrir(vacante.id) }}
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
