"use client"

import Link from "next/link"
import { ChevronRight, Pencil, Power, PowerOff } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Empresa } from "@/types/empresa"

import { COLUMNAS, ESTADO_ESTILO } from "./_grillaEmpresas"

interface EmpresasTableProps {
  empresas: Empresa[]
  loading: boolean
  error: boolean
  canWrite: boolean
  onRetry: () => void
  onEdit: (empresa: Empresa) => void
  onToggle: (empresa: Empresa) => void
  togglingId: string | null
  /** Qué ofrecer cuando no hay datos: el alta. `undefined` si no puede escribir. */
  accionVacio?: ReactNode
}

/** Guion para un valor vacío: una celda en blanco no distingue "sin dato" de "no cargó". */
function Vacio() {
  return <span className="italic text-muted-foreground/60">—</span>
}

const ACCION_CLASS =
  "flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50"

/**
 * Tabla de empresas con edición y toggle de activa por fila (solo canWrite).
 *
 * 🔴 AHORA ES DUEÑA DE SUS TRES ESTADOS (carga, error, vacío) y antes no lo era: los tenía la
 * página, con `return` tempranos que **reemplazaban la pantalla entera** durante la carga. El
 * patrón del bloque B los necesita acá: el vacío es una fila con `colSpan`, y para eso tiene que
 * estar adentro de la `<Table>`.
 *
 * ⚠️ `TablaVacia` SE USA CON `chips=[]` Y UN `onLimpiarTodo` QUE NO HACE NADA, y es correcto:
 * esta pantalla **no tiene un solo filtro** —`GET /api/empresas` no acepta ningún Query— así que
 * el vacío sólo puede caer en la rama "todavía no hay nada", que es la que no usa ninguno de los
 * dos. Se delega igual en el primitivo en vez de escribir el copy a mano para que el texto y la
 * forma sigan saliendo de un solo lugar.
 */
export function EmpresasTable({
  empresas, loading, error, canWrite, onRetry, onEdit, onToggle, togglingId, accionVacio,
}: EmpresasTableProps) {
  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó.
  if (error) return <ErrorState description="No se pudieron cargar las empresas." action={onRetry} />

  return (
    <Table patron="datos">
      <Encabezado columnas={COLUMNAS} />
      {loading ? (
        <FilasEsqueleto columnas={COLUMNAS} />
      ) : empresas.length === 0 ? (
        <TablaVacia
          colSpan={COLUMNAS.length}
          chips={[]}
          sustantivo="empresas"
          genero="femenino"
          onLimpiarTodo={() => {}}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {empresas.map((empresa) => (
            <TableRow key={empresa.id} className="group">
              <TableCell className="font-medium">
                <Link href={`/empresas/${empresa.id}`} className="hover:underline hover:text-primary">
                  {empresa.nombre}
                </Link>
              </TableCell>
              <TableCell className="font-mono text-sm text-muted-foreground">
                {empresa.cuit ?? <Vacio />}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {empresa.email ?? <Vacio />}
              </TableCell>
              <TableCell>
                {/* El estilo sale de `_grillaEmpresas`: ninguno de los dos es azul. */}
                <Badge variant="outline" className={empresa.activa ? ESTADO_ESTILO.activa : ESTADO_ESTILO.inactiva}>
                  {empresa.activa ? "Activa" : "Inactiva"}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                {/* 🔴 SIEMPRE VISIBLES, sólo cambian de color al apuntar (§3). El chevron va
                    incluso sin permiso de escritura: abrir la ficha de la empresa es una LECTURA
                    y la sección EMPRESA la tiene todo el que llega a esta pantalla, así que no
                    manda a nadie a una ruta que el AuthGuard rebote. */}
                <div className="flex justify-end gap-1">
                  {canWrite && (
                    <>
                      <button type="button" aria-label={`Editar ${empresa.nombre}`} onClick={() => onEdit(empresa)}
                        className={`${ACCION_CLASS} group-hover:text-primary`}>
                        <Pencil className="size-4" aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        aria-label={empresa.activa ? `Desactivar ${empresa.nombre}` : `Activar ${empresa.nombre}`}
                        onClick={() => onToggle(empresa)}
                        disabled={togglingId === empresa.id}
                        className={`${ACCION_CLASS} group-hover:text-primary`}
                      >
                        {empresa.activa ? <PowerOff className="size-4" aria-hidden="true" /> : <Power className="size-4" aria-hidden="true" />}
                      </button>
                    </>
                  )}
                  <Link
                    href={`/empresas/${empresa.id}`}
                    aria-label={`Ver la ficha de ${empresa.nombre}`}
                    className={`${ACCION_CLASS} group-hover:text-primary`}
                  >
                    <ChevronRight className="size-4" aria-hidden="true" />
                  </Link>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
