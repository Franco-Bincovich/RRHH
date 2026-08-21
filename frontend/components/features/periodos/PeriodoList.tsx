"use client"

import { CalendarClock, Undo2 } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { MODULO_LABEL } from "@/services/periodos"
import type { Periodo } from "@/types/periodo"

import { COLUMNAS, ESTADO_ESTILO } from "./_grillaPeriodos"

interface Props {
  periodos: Periodo[]
  loading: boolean
  error: boolean
  nombreUsuario: (id: string | null) => string
  canWrite: boolean
  onRetry: () => void
  onReabrir: (p: Periodo) => void
}

/**
 * Tabla de períodos: módulo, rango, estado, quién/cuándo, y acción de reabrir si está cerrado.
 *
 * 🔴 AHORA ES DUEÑA DE SUS TRES ESTADOS (carga, error, vacío) y antes no lo era: los tenía la
 * página, y el vacío era un `<p>` con borde que reemplazaba la tabla entera. El patrón del bloque
 * B los necesita acá, adentro de la `<Table>`.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 EL VACÍO USA LA ESTRUCTURA DEL PATRÓN CON COPY PROPIO, Y NO `TablaVacia`.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * `TablaVacia` arma su texto con `textoVacio()`, que sin filtros dice *"Todavía no hay X · Cuando
 * se cargue el primero va a aparecer acá"*. Acá esa frase falla por dos lados a la vez:
 *
 *   · **un período no se "carga", se CIERRA**, y quien lo hace es `admin_rrhh` desde el formulario
 *     que está justo arriba de esta tabla. `gerencia_lectura` ve la pantalla y no puede cerrar
 *     ninguno: para ese usuario "cuando se cargue el primero" es una instrucción que no puede
 *     seguir. Es exactamente el caso que la regla del bloque describe.
 *   · **la ausencia acá SIGNIFICA algo**, y es lo más útil que la pantalla puede decir: si no hay
 *     ningún período cerrado, TODO registro se puede editar sin restricción de fecha. "Todavía no
 *     hay períodos" es verdadero y no contesta la pregunta que trajo al usuario hasta acá.
 *
 * Lo que sí se conserva es la ESTRUCTURA: la fila con `colSpan`, el `data-vacio` que la excluye
 * del hover de datos (`tablePatron.ts`) y el encabezado intacto. Molde: `EquipoTable`.
 */
export function PeriodoList({
  periodos, loading, error, nombreUsuario, canWrite, onRetry, onReabrir,
}: Props) {
  const columnas = COLUMNAS.filter((c) => c.clave !== "acciones" || canWrite)

  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó.
  if (error) return <ErrorState action={onRetry} />

  return (
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : periodos.length === 0 ? (
        <TableBody>
          {/* `data-vacio`: el patrón de tabla excluye esta fila del hover de datos. `h-auto` gana
              al 46px de las filas: acá la fila no es una fila, es el panel entero. */}
          <TableRow data-vacio="" className="hover:bg-transparent">
            <TableCell colSpan={columnas.length} className="h-auto whitespace-normal p-0">
              <EmptyState
                icon={<CalendarClock />}
                title="Todavía no hay períodos cerrados"
                description="Mientras no haya ninguno, cualquier registro se puede cargar y editar sin restricción de fecha."
              />
            </TableCell>
          </TableRow>
        </TableBody>
      ) : (
        <TableBody>
          {periodos.map((p) => {
            const cerrado = p.estado === "cerrado"
            return (
              <TableRow key={p.id} className="group">
                <TableCell className="font-medium text-foreground">
                  {p.modulo ? MODULO_LABEL[p.modulo] ?? p.modulo : "Todos los módulos"}
                </TableCell>
                <TableCell className="whitespace-nowrap tabular-nums">{p.desde}</TableCell>
                <TableCell className="whitespace-nowrap tabular-nums">{p.hasta}</TableCell>
                <TableCell>
                  {/* El estilo sale de `_grillaPeriodos`: ninguno de los dos es azul, y la
                      semántica es la contraintuitiva — cerrado es el control PUESTO. */}
                  <Badge variant="outline" className={cerrado ? ESTADO_ESTILO.cerrado : ESTADO_ESTILO.reabierto}>
                    {cerrado ? "Cerrado" : "Reabierto"}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {cerrado
                    ? `Cerrado por ${nombreUsuario(p.cerrado_por)} el ${p.cerrado_at.slice(0, 10)}`
                    : `Reabierto por ${nombreUsuario(p.reabierto_por)} el ${(p.reabierto_at ?? "").slice(0, 10)}`}
                </TableCell>
                {canWrite && (
                  <TableCell className="text-right">
                    {/* Siempre visible mientras el período esté cerrado (que es cuando la acción
                        existe), y sólo cambia de color al apuntar la fila. */}
                    {cerrado && (
                      <button
                        type="button"
                        onClick={() => onReabrir(p)}
                        aria-label={`Reabrir el período de ${p.desde} a ${p.hasta}`}
                        className="ml-auto flex h-8 items-center gap-1.5 rounded-md px-2 text-xs text-muted-foreground transition-colors group-hover:text-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                      >
                        <Undo2 className="size-4" aria-hidden="true" /> Reabrir
                      </button>
                    )}
                  </TableCell>
                )}
              </TableRow>
            )
          })}
        </TableBody>
      )}
    </Table>
  )
}
