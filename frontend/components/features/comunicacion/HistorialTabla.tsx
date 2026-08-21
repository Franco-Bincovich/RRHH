"use client"

import { MailX } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorCarga } from "@/components/ui/ErrorCarga"
import { TablaVacia } from "@/components/ui/TablaVacia"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto, type Columna } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { MailEnviado } from "@/types/plantillas"

export const ERROR_HISTORIAL = "No se pudo cargar el historial de mails."
export const VACIO_HISTORIAL = "Todavía no se envió ningún mail."

/**
 * La grilla del historial. `Destinatario` absorbe el espacio libre: lleva el mail y, debajo, el
 * asunto renderizado, que es texto de largo impredecible.
 */
const COLUMNAS: Columna[] = [
  { clave: "fecha", label: "Fecha", ancho: "w-[16%]" },
  { clave: "destinatario", label: "Destinatario", ancho: "" },
  { clave: "plantilla", label: "Plantilla", ancho: "w-[18%]" },
  { clave: "estado", label: "Estado", ancho: "w-[22%]" },
]

interface Props {
  items: MailEnviado[]
  cargando: boolean
  /** La consulta FALLÓ. Distinto de `items: []`, que es un historial vacío de verdad. */
  error: boolean
  /** Los filtros activos: cambian el texto del vacío, porque el motivo del vacío es otro. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  onReintentar: () => void
}

/** `2026-08-07T13:04:22Z` → `07/08/2026 13:04`. Sin librería: es la única fecha de la pantalla. */
function fecha(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const p = (n: number) => String(n).padStart(2, "0")
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`
}

/**
 * La tabla del historial. Presentacional puro: sin fetch, sin estado, sin filtros propios.
 *
 * 🔴 TRES ESTADOS DISTINGUIBLES —cargando · error · lista (vacía o no)— y el del medio NO se
 * muestra como los otros dos. Un `.catch` que pinte lista vacía diría "todavía no se envió
 * ningún mail" cuando lo que hubo fue un fallo de red, y eso es peor que un error: es una
 * afirmación falsa sobre los datos. Es el bug que este repo ya se comió con "no hay empleados".
 *
 * El vacío distingue además "no hay nada" de "no hay nada CON ESTE FILTRO": son dos situaciones
 * distintas y la salida también (esperar vs. limpiar el filtro).
 *
 * ⚠️ EL VACÍO CON FILTROS AHORA ES `TablaVacia` Y ARMA LA FRASE CON LOS VALORES REALES ("No hay
 * mails con estado No entregados"), en vez del genérico "Ningún mail coincide con el filtro" que
 * tenía. El vacío SIN filtros conserva copy propio: nadie "carga" un mail enviado —lo produce el
 * sistema al mandar—, así que el "Cuando se cargue el primero" de `textoVacio` sería falso. Es la
 * misma decisión que en /auditoria, y por el mismo motivo.
 *
 * El motivo del fallo se muestra en la fila, no en un tooltip ni detrás de un clic: es
 * exactamente el dato que alguien viene a buscar cuando pregunta "¿por qué no le llegó?".
 */
export function HistorialTabla({ items, cargando, error, chips, onLimpiarTodo, onReintentar }: Props) {
  if (error) return <ErrorCarga mensaje={ERROR_HISTORIAL} onReintentar={onReintentar} />

  return (
    <Table patron="datos">
      <Encabezado columnas={COLUMNAS} />
      {cargando ? (
        <FilasEsqueleto columnas={COLUMNAS} />
      ) : items.length === 0 ? (
        chips.length > 0 ? (
          <TablaVacia
            colSpan={COLUMNAS.length}
            chips={chips}
            sustantivo="mails"
            onLimpiarTodo={onLimpiarTodo}
          />
        ) : (
          <TableBody>
            <TableRow data-vacio="" className="hover:bg-transparent">
              <TableCell colSpan={COLUMNAS.length} className="h-auto whitespace-normal p-0">
                <EmptyState
                  icon={<MailX />}
                  title={VACIO_HISTORIAL}
                  description="Cada mail que salga desde la pestaña de plantillas queda registrado acá, con su destinatario y —si falló— el motivo."
                />
              </TableCell>
            </TableRow>
          </TableBody>
        )
      ) : (
        <TableBody>
          {items.map((m) => (
            <TableRow key={m.id} className="group">
              <TableCell className="whitespace-nowrap tabular-nums text-muted-foreground">{fecha(m.created_at)}</TableCell>
              <TableCell>
                <span className="text-foreground">{m.destinatario}</span>
                <span className="block truncate text-xs text-muted-foreground">{m.asunto_render}</span>
              </TableCell>
              <TableCell className="text-muted-foreground">{m.plantilla_clave ?? "—"}</TableCell>
              <TableCell>
                {m.estado === "enviado" ? (
                  <span className="text-emerald-700 dark:text-emerald-500">Enviado</span>
                ) : (
                  <>
                    <span className="text-amber-700 dark:text-amber-500">No se entregó</span>
                    {m.error && (
                      <span className="block text-xs text-muted-foreground">{m.error}</span>
                    )}
                  </>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
