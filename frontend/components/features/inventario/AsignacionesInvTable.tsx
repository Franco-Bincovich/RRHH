"use client"

/**
 * Tabla de asignaciones de inventario: presentacional. Dueña de los cuatro estados del listado
 * (cargando / error / vacío / datos) y sin saber nada de filtros ni de fetch.
 *
 * 🔴 MUESTRA SÓLO ASIGNACIONES VIGENTES: el repo filtra `fecha_devolucion IS NULL`
 * (`inventario_asignaciones_repo.find_all`). Eso NO es un filtro que el usuario pueda tocar, así
 * que no produce chip — y por eso el vacío SIN filtros lleva copy propio: ver abajo.
 */
import { PackageOpen } from "lucide-react"
import type { ReactNode } from "react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Asignacion } from "@/types/inventario"

import { COLUMNAS_ASIGNACIONES } from "./_grillaInventario"

function formatDate(s: string | null): string {
  if (!s) return "—"
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y}`
}

interface AsignacionesInvTableProps {
  asignaciones: Asignacion[]
  loading: boolean
  error: boolean
  canWrite: boolean
  mostrarEmpresa: boolean
  onReload: () => void
  onDevolver: (a: Asignacion) => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos. `undefined` sin permiso. */
  accionVacio?: ReactNode
}

export function AsignacionesInvTable({
  asignaciones, loading, error, canWrite, mostrarEmpresa, onReload, onDevolver,
  chips, onLimpiarTodo, accionVacio,
}: AsignacionesInvTableProps) {
  const columnas = COLUMNAS_ASIGNACIONES
    .filter((c) => c.clave !== "empresa" || mostrarEmpresa)
    .filter((c) => c.clave !== "acciones" || canWrite)

  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó.
  if (error) return <ErrorState action={onReload} />

  return (
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : asignaciones.length === 0 ? (
        chips.length > 0 ? (
          <TablaVacia
            colSpan={columnas.length}
            chips={chips}
            sustantivo="asignaciones activas"
            genero="femenino"
            onLimpiarTodo={onLimpiarTodo}
            accion={accionVacio}
          />
        ) : (
          /*
           * ═══════════════════════════════════════════════════════════════════════════════════
           * 🔴 SIN FILTROS VA COPY PROPIO, y el motivo es el `fecha_devolucion IS NULL` de arriba.
           * ═══════════════════════════════════════════════════════════════════════════════════
           * `textoVacio` diría *"Todavía no hay asignaciones activas · Cuando se cargue la primera
           * va a aparecer acá"*, y eso confunde dos cosas distintas: esta tabla puede estar vacía
           * con el inventario ENTERO asignado y devuelto a lo largo del año. No es "todavía no
           * hay", es "hoy no hay nada afuera" — que es una respuesta, no una carencia.
           */
          <TableBody>
            <TableRow data-vacio="" className="hover:bg-transparent">
              <TableCell colSpan={columnas.length} className="h-auto whitespace-normal p-0">
                <EmptyState
                  icon={<PackageOpen />}
                  title="No hay ítems asignados en este momento"
                  description="Esta lista muestra sólo las asignaciones vigentes: lo que ya se devolvió no aparece acá, queda en el historial de cada ítem."
                  action={accionVacio}
                />
              </TableCell>
            </TableRow>
          </TableBody>
        )
      ) : (
        <TableBody>
          {asignaciones.map((a) => (
            <TableRow key={a.id} className="group">
              <TableCell className="font-medium">{a.empleado_nombre ?? "—"}</TableCell>
              <TableCell>{a.item_nombre ?? "—"}</TableCell>
              <TableCell className="text-muted-foreground">{a.item_tipo ?? "—"}</TableCell>
              <TableCell className="text-muted-foreground">{a.item_numero_serie ?? "—"}</TableCell>
              {mostrarEmpresa && <TableCell className="text-muted-foreground">{a.empresa_nombre ?? "—"}</TableCell>}
              <TableCell className="text-muted-foreground tabular-nums">{formatDate(a.fecha_asignacion)}</TableCell>
              {canWrite && (
                <TableCell className="text-right">
                  {/* Siempre visible, sólo cambia de color al apuntar la fila (§3). */}
                  <button
                    type="button"
                    onClick={() => onDevolver(a)}
                    aria-label={`Devolver ${a.item_nombre ?? "el ítem"} de ${a.empleado_nombre ?? "el colaborador"}`}
                    className="ml-auto flex h-8 items-center rounded-md px-2 text-xs text-muted-foreground transition-colors group-hover:text-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                  >
                    Devolver
                  </button>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
