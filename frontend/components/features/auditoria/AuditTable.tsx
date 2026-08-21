import { ScrollText } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import {
  ENTIDAD_LABEL, EVENTO_LABEL, formatFechaHora, resumenDiff,
} from "@/components/features/auditoria/auditLabels"
import type { AuditLog } from "@/types/auditoria"

import { COLUMNAS } from "./_grillaAuditoria"

interface Props {
  logs: AuditLog[]
  onVerDetalle: (log: AuditLog) => void
  /**
   * 🔴 LOS ESTADOS SON OPCIONALES, Y ESO ES EL ALCANCE, NO UNA DUDA.
   *
   * Esta tabla tiene DOS consumidores y son pantallas distintas: el listado de `/auditoria`, que
   * le pasa los tres estados y sus chips —ahí manda el patrón del bloque B—, y la sección
   * "Historial de cambios" de la ficha de un empleado, que es una tabla EMBEBIDA con su propio
   * esqueleto compacto de dos barras y su propio vacío ("Sin cambios registrados", que habla de
   * ESE legajo y no del sistema). Hacer los estados obligatorios habría forzado a la ficha a
   * mostrar el copy del listado —"No hay registros de auditoría todavía"— sobre un colaborador
   * puntual, que dice algo distinto y falso.
   *
   * Con los defaults de abajo, un consumidor que ya resuelve sus estados le pasa sólo `logs` y
   * la tabla sale exactamente como salía.
   */
  loading?: boolean
  error?: boolean
  onRetry?: () => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips?: ChipFiltro[]
  onLimpiarTodo?: () => void
}

/**
 * Tabla de eventos de auditoría. Dueña de sus tres estados (carga, error, vacío) — antes los
 * tenía la página, con un esqueleto de barras sueltas que no compartía columnas con la tabla y un
 * `<EmptyState>` que la reemplazaba entera. El patrón del bloque B los necesita acá.
 *
 * La columna Detalle muestra un resumen legible del cambio + un botón "Ver detalle" que abre el
 * modal vía `onVerDetalle`.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 EL VACÍO TIENE DOS TEXTOS, Y NO ES INDECISIÓN: SON DOS PANTALLAS DISTINTAS.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * **Con filtros** va `TablaVacia`, que arma la frase con los valores reales ("No hay registros de
 * auditoría con sección Vacaciones y evento Alta") y ofrece las dos salidas del patrón.
 *
 * **Sin filtros** va copy PROPIO, porque el genérico de `textoVacio` sería falso: dice *"Cuando se
 * cargue el primero va a aparecer acá"*, y **nadie carga un evento de auditoría**. Los produce el
 * sistema al escribir, y esta sección es de solo lectura por diseño ("el sistema escribe el audit,
 * no el usuario", `routers/auditoria.py`). Es exactamente el caso que la regla del bloque
 * describe: la frase sin filtros tiene que ser verdad para quien mira la pantalla.
 *
 * Lo que se conserva en las dos ramas es la ESTRUCTURA: la fila con `colSpan`, el `data-vacio`
 * que la excluye del hover de datos (`tablePatron.ts`) y el encabezado intacto.
 */
export function AuditTable({
  logs, onVerDetalle,
  loading = false, error = false, onRetry = () => {}, chips = [], onLimpiarTodo = () => {},
}: Props) {
  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó.
  if (error) return <ErrorState action={onRetry} />

  return (
    <Table patron="datos">
      <Encabezado columnas={COLUMNAS} />
      {loading ? (
        <FilasEsqueleto columnas={COLUMNAS} />
      ) : logs.length === 0 ? (
        chips.length > 0 ? (
          /* Sin `claveSujeto`: el sujeto sería la EMPRESA y acá no es un chip — la manda el
             selector del sidebar. La frase arranca impersonal. */
          <TablaVacia
            colSpan={COLUMNAS.length}
            chips={chips}
            sustantivo="registros de auditoría"
            onLimpiarTodo={onLimpiarTodo}
          />
        ) : (
          <TableBody>
            <TableRow data-vacio="" className="hover:bg-transparent">
              <TableCell colSpan={COLUMNAS.length} className="h-auto whitespace-normal p-0">
                <EmptyState
                  icon={<ScrollText />}
                  title="No hay registros de auditoría todavía"
                  description="Los cambios realizados en el sistema aparecen acá a medida que ocurren. Nadie los carga a mano."
                />
              </TableCell>
            </TableRow>
          </TableBody>
        )
      ) : (
        <TableBody>
          {logs.map((log) => (
            <TableRow key={log.id} className="group">
              <TableCell className="whitespace-nowrap tabular-nums">{formatFechaHora(log.created_at)}</TableCell>
              <TableCell>{log.usuario_nombre ?? "Sistema"}</TableCell>
              <TableCell className="text-muted-foreground">{log.empresa_nombre ?? "—"}</TableCell>
              <TableCell>{ENTIDAD_LABEL[log.entidad] ?? log.entidad}</TableCell>
              <TableCell>{EVENTO_LABEL[log.evento] ?? log.evento}</TableCell>
              <TableCell>
                <Badge variant="outline">{log.accion}</Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground text-sm">
                    {resumenDiff(log.datos_anteriores, log.datos_nuevos)}
                  </span>
                  {/* 🔴 SIEMPRE VISIBLE, sólo cambia de color al apuntar (§3). Revelarlo en hover
                      obliga a barrer la tabla con el mouse para descubrir que el detalle existe —
                      y en un log de auditoría el detalle ES la pantalla. */}
                  <button
                    type="button"
                    onClick={() => onVerDetalle(log)}
                    className="shrink-0 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors group-hover:text-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                  >
                    Ver detalle
                  </button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
