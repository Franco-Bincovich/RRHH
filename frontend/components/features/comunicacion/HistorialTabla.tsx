"use client"

import { ErrorCarga } from "@/components/ui/ErrorCarga"
import type { MailEnviado } from "@/types/plantillas"

export const ERROR_HISTORIAL = "No se pudo cargar el historial de mails."
export const VACIO_HISTORIAL = "Todavía no se envió ningún mail."

interface Props {
  items: MailEnviado[]
  cargando: boolean
  /** La consulta FALLÓ. Distinto de `items: []`, que es un historial vacío de verdad. */
  error: boolean
  /** Hay filtros puestos: cambia el texto del vacío, porque el motivo del vacío es otro. */
  filtrado: boolean
  onReintentar: () => void
}

const TH = "px-3 py-2 text-left text-xs font-medium text-muted-foreground"
const TD = "px-3 py-2 align-top"

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
 * El motivo del fallo se muestra en la fila, no en un tooltip ni detrás de un clic: es
 * exactamente el dato que alguien viene a buscar cuando pregunta "¿por qué no le llegó?".
 */
export function HistorialTabla({ items, cargando, error, filtrado, onReintentar }: Props) {
  if (error) return <ErrorCarga mensaje={ERROR_HISTORIAL} onReintentar={onReintentar} />

  if (cargando) {
    return (
      <div className="space-y-2" aria-busy="true">
        {[0, 1, 2].map((i) => <div key={i} className="h-9 animate-pulse rounded-md bg-muted" />)}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
        {filtrado ? "Ningún mail coincide con el filtro." : VACIO_HISTORIAL}
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="border-b bg-muted/40">
          <tr>
            <th className={TH}>Fecha</th>
            <th className={TH}>Destinatario</th>
            <th className={TH}>Plantilla</th>
            <th className={TH}>Estado</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {items.map((m) => (
            <tr key={m.id}>
              <td className={`${TD} whitespace-nowrap text-muted-foreground`}>{fecha(m.created_at)}</td>
              <td className={TD}>
                <span className="text-foreground">{m.destinatario}</span>
                <span className="block truncate text-xs text-muted-foreground">{m.asunto_render}</span>
              </td>
              <td className={`${TD} text-muted-foreground`}>{m.plantilla_clave ?? "—"}</td>
              <td className={TD}>
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
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
