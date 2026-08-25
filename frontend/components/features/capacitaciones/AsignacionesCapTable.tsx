"use client"

/**
 * Tabla de asignaciones de capacitación: presentacional. Cubre los cuatro estados del listado
 * (cargando / error / vacío / datos) y no sabe nada de filtros ni de fetch — extraída de
 * AsignacionesTab, que estaba en 211 líneas contra un límite de 150.
 */
import { Pencil, Trash2 } from "lucide-react"
import { AccionFila } from "@/components/ui/AccionFila"
import type { ReactNode } from "react"

import { CertificadoCell } from "@/components/features/capacitaciones/CertificadoCell"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"

import {
  COLUMNAS_ASIGNACIONES, ESTADO_ASIGNACION_ESTILO, ESTADO_ASIGNACION_LABEL,
} from "./_grillaCapacitaciones"
import type { Asignacion } from "@/types/capacitacion"

function formatFecha(s: string | null): string {
  if (!s) return "—"
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y}`
}

interface AsignacionesCapTableProps {
  asignaciones: Asignacion[]
  loading: boolean
  error: boolean
  canWrite: boolean
  mostrarEmpresa: boolean
  deletingId: string | null
  onReload: () => void
  onEditarEstado: (a: Asignacion) => void
  onEliminar: (id: string) => void
  /**
   * Los filtros activos, para explicar el vacío con sus valores reales. OPCIONALES: esta tabla
   * la usa también `AsignacionesCapTable.test.tsx` con el camino de datos, y el molde del repo es
   * que un consumidor que no filtra no tenga que inventar un array vacío en cada render.
   */
  chips?: ChipFiltro[]
  onLimpiarTodo?: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos. `undefined` sin permiso. */
  accionVacio?: ReactNode
}

export function AsignacionesCapTable({
  asignaciones, loading, error, canWrite, mostrarEmpresa, deletingId,
  onReload, onEditarEstado, onEliminar, chips = [], onLimpiarTodo = () => {}, accionVacio,
}: AsignacionesCapTableProps) {
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
        /* Sin `claveSujeto`: el sujeto sería la EMPRESA y acá es un chip más — la asignación es
           de una PERSONA, no de una sociedad. La frase arranca impersonal. */
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="asignaciones"
          genero="femenino"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
      <TableBody>
        {asignaciones.map((a) => (
          <TableRow key={a.id} className="group">
            {/*
              Fila sin empleado vinculado (mig 116): se muestra el nombre crudo del Excel TAL
              CUAL y la marca va al lado, nunca dentro del nombre. Molde exacto:
              EvaluadosResultadosTable.tsx, que resuelve el mismo problema con nombres de CSV.
              🔴 Dice "Sin vincular" y no "Sin asignar" (el literal de evaluaciones) porque acá
              el módulo ENTERO se llama asignaciones: "sin asignar" se leería como "el curso no
              está asignado", que es lo contrario de lo que pasa. "Sin vincular" ya es el literal
              del repo para esto (usuarios/EmpleadoLiderSelect.tsx).
            */}
            <TableCell className="font-medium">
              {a.empleado_nombre ?? a.nombre_libre ?? "—"}
              {!a.empleado_id && <Badge variant="outline" className="ml-2">Sin vincular</Badge>}
            </TableCell>
            <TableCell>{a.capacitacion_nombre ?? "—"}</TableCell>
            <TableCell>
              {/* El estilo sale de `_grillaCapacitaciones`: ninguno de los tres es azul.
                  "Completado" venía con `variant="default"`, o sea `bg-primary`. */}
              <Badge variant="outline" className={ESTADO_ASIGNACION_ESTILO[a.estado] ?? ""}>
                {ESTADO_ASIGNACION_LABEL[a.estado] ?? a.estado}
              </Badge>
            </TableCell>
            {mostrarEmpresa && <TableCell className="text-muted-foreground">{a.empresa_nombre ?? "—"}</TableCell>}
            <TableCell className="text-muted-foreground">{formatFecha(a.fecha_limite)}</TableCell>
            <TableCell className="text-muted-foreground">{formatFecha(a.fecha_completado)}</TableCell>
            <TableCell>
              <CertificadoCell
                asignacionId={a.id}
                hasCertificado={Boolean(a.certificado_url)}
                canWrite={canWrite}
                onUploaded={onReload}
              />
            </TableCell>
            {canWrite && (
              <TableCell className="text-right">
                {/* 🔴 SIEMPRE VISIBLES, sólo cambian de color al apuntar (§3). El rojo del
                    borrado aparece recién con el mouse en la fila. */}
                <div className="flex justify-end gap-1">
                  <AccionFila onClick={() => onEditarEstado(a)}
                    aria-label={`Cambiar el estado de ${a.empleado_nombre ?? a.nombre_libre ?? "la asignación"}`}>
                    <Pencil className="size-4" aria-hidden="true" />
                  </AccionFila>
                  <AccionFila tono="destructivo" onClick={() => onEliminar(a.id)} disabled={deletingId === a.id}
                    aria-label={`Eliminar la asignación de ${a.empleado_nombre ?? a.nombre_libre ?? "la fila"}`}>
                    <Trash2 className="size-4" aria-hidden="true" />
                  </AccionFila>
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
