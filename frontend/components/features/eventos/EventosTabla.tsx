"use client"

import { Check, Pencil, RotateCcw, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Evento } from "@/types/evento"

import { COLUMNAS, ESTADO_ESTILO, VISIBILIDAD_ESTILO } from "./_grillaEventos"

/**
 * 🔴 EL `T00:00:00` NO ES DECORATIVO. `new Date("2026-10-01")` parsea como UTC medianoche, y en
 * Argentina (UTC-3) eso se renderiza como el 30/09: la agenda mostraría todos los eventos un día
 * antes. Con la hora explícita el string se interpreta como local. Misma función y mismo motivo
 * que en `proyectos/HorasTab.tsx`; el repo todavía no tiene un formateador compartido.
 */
function formatFecha(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(
    "es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

interface Props {
  eventos: Evento[]
  loading: boolean
  error: string | null
  canWrite: boolean
  onRetry: () => void
  onEdit: (e: Evento) => void
  onDelete: (e: Evento) => void
  onResuelta: (e: Evento, resuelta: boolean) => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` sin permiso. */
  accionVacio?: ReactNode
}

const ACCION_CLASS =
  "flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

/**
 * Tabla de la agenda. PRESENTACIONAL: sin fetch ni lógica de negocio.
 *
 * 🔴 AHORA ES DUEÑA DE SUS TRES ESTADOS (carga, error, vacío) y antes no lo era: los tenía la
 * página, con `return` tempranos que **reemplazaban la pantalla entera** durante la carga. El
 * patrón del bloque B los necesita acá: el vacío es una fila con `colSpan`, y para eso tiene que
 * estar adentro de la `<Table>`.
 *
 * ⚠️ Los botones de escritura se OMITEN cuando `canWrite` es false, no se deshabilitan. Un
 * `disabled` sobre el `Button` de shadcn no se puede afirmar en un test —el markup trae la clase
 * `disabled:...` de Tailwind SIEMPRE— y además un botón muerto invita a clickearlo. Es la regla
 * que dejó escrita `ClientesTabla`.
 *
 * 🔑 El botón de resolver cambia de ICONO Y DE ETIQUETA según el estado, y llama al MISMO
 * handler con el valor que quiere. No hay dos acciones: resolver es reversible, y el front manda
 * el estado deseado en vez de un incremento sobre uno que puede estar viejo.
 */
export function EventosTabla({
  eventos, loading, error, canWrite, onRetry, onEdit, onDelete, onResuelta,
  chips, onLimpiarTodo, accionVacio,
}: Props) {
  const columnas = COLUMNAS.filter((c) => c.clave !== "acciones" || canWrite)

  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó.
  if (error) return <ErrorState description={error} action={onRetry} />

  return (
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : eventos.length === 0 ? (
        /* Sin `claveSujeto`: el sujeto sería la EMPRESA y acá no es un chip — la manda el
           selector del sidebar. La frase arranca impersonal. */
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="eventos"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {eventos.map((e) => (
            <TableRow key={e.id} className="group">
              <TableCell className="font-medium">
                {e.nombre}
                {e.descripcion && (
                  <p className="text-xs font-normal text-muted-foreground">{e.descripcion}</p>
                )}
              </TableCell>
              <TableCell className="tabular-nums">{formatFecha(e.fecha)}</TableCell>
              <TableCell className="tabular-nums">{e.dias_aviso} días antes</TableCell>
              <TableCell>
                {/* El estilo sale de `_grillaEventos`: ninguno de los dos es azul, y la
                    visibilidad no es un eje bueno/malo. Ver el 🔴 de ese archivo. */}
                <Badge variant="outline" className={e.es_publica ? VISIBILIDAD_ESTILO.publica : VISIBILIDAD_ESTILO.privada}>
                  {e.es_publica ? "Del equipo" : "Privado"}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className={e.resuelta ? ESTADO_ESTILO.resuelto : ESTADO_ESTILO.pendiente}>
                  {e.resuelta
                    ? `Resuelto${e.resuelta_por_nombre ? ` por ${e.resuelta_por_nombre}` : ""}`
                    : "Pendiente"}
                </Badge>
              </TableCell>
              {canWrite && (
                <TableCell className="text-right">
                  {/* 🔴 SIEMPRE VISIBLES, sólo cambian de color al apuntar (§3). El rojo del
                      borrado aparece recién con el mouse en la fila: en reposo, una columna de
                      tachos rojos se lee como una lista de errores. */}
                  <div className="flex justify-end gap-1">
                    <button
                      type="button"
                      aria-label={`${e.resuelta ? "Reabrir" : "Resolver"} ${e.nombre}`}
                      onClick={() => onResuelta(e, !e.resuelta)}
                      className={`${ACCION_CLASS} group-hover:text-primary`}
                    >
                      {e.resuelta ? <RotateCcw className="size-4" aria-hidden="true" /> : <Check className="size-4" aria-hidden="true" />}
                    </button>
                    <button type="button" aria-label={`Editar ${e.nombre}`} onClick={() => onEdit(e)}
                      className={`${ACCION_CLASS} group-hover:text-primary`}>
                      <Pencil className="size-4" aria-hidden="true" />
                    </button>
                    <button type="button" aria-label={`Eliminar ${e.nombre}`} onClick={() => onDelete(e)}
                      className={`${ACCION_CLASS} group-hover:text-destructive`}>
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
