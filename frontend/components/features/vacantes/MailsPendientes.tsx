"use client"

import { useCallback, useEffect, useState } from "react"
import { Inbox, Paperclip } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { asignarMail, fetchMailsPendientes, fetchVacantes } from "@/services/vacantes"
import type { MailPendiente, Vacante } from "@/types/vacantes"

/**
 * Los mails de la casilla que no matchearon ninguna búsqueda, con el selector para asignarlos.
 *
 * 🔴 NO HAY ESTADO PERSISTIDO: la lista se relee de Gmail cada vez. La casilla es la fuente de
 * verdad, así que no hay dos estados que sincronizar. Un mail asignado desaparece solo —al crear
 * el candidato se guarda su `gmail_message_id` y la lectura siguiente lo saltea—, y para
 * descartar uno sin asignarlo RRHH lo archiva o etiqueta EN GMAIL. Por eso acá no hay botón de
 * "descartar": sería un segundo estado del que el buzón no se entera.
 *
 * ⚠️ `adjuntos_validos` viene contado por el backend SIN bajar los archivos (extensión + tamaño
 * declarado). Un mail con 0 no se puede asignar: no crearía ningún candidato.
 */
const MOTIVO: Record<string, string> = {
  sin_codigo: "Sin código en el asunto",
  codigo_ambiguo: "Más de un código en el asunto",
  vacante_desconocida: "El código no corresponde a ninguna búsqueda",
}

export function MailsPendientes() {
  const [mails, setMails] = useState<MailPendiente[]>([])
  const [vacantes, setVacantes] = useState<Vacante[]>([])
  const [elegida, setElegida] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [asignando, setAsignando] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const cargar = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [m, v] = await Promise.all([fetchMailsPendientes(), fetchVacantes()])
      setMails(m)
      setVacantes(v)
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron leer los mails pendientes.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  async function asignar(messageId: string) {
    const vacanteId = elegida[messageId]
    if (!vacanteId) return
    setAsignando(messageId)
    setError(null)
    try {
      await asignarMail(messageId, vacanteId)
      // Se saca de la lista sin recargar: el backend ya lo va a saltear en la próxima lectura.
      setMails((prev) => prev.filter((m) => m.message_id !== messageId))
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo asignar el mail.")
    } finally {
      setAsignando(null)
    }
  }

  if (loading) return <Skeleton className="h-40 w-full rounded-xl" />

  return (
    <div className="mt-8">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-foreground">
          Mails sin asignar {mails.length > 0 && `(${mails.length})`}
        </h2>
        <Button variant="ghost" size="sm" className="min-h-10" onClick={cargar}>Actualizar</Button>
      </div>

      {error && <p className="mb-3 text-sm text-destructive">{error}</p>}

      {mails.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-8 text-center">
          <Inbox className="mx-auto mb-3 size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No hay mails con adjuntos esperando asignación.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {mails.map((m) => (
            <div key={m.message_id} className="rounded-lg border bg-card p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{m.remitente || "(sin remitente)"}</p>
                  <p className="truncate text-sm text-muted-foreground">{m.asunto || "(sin asunto)"}</p>
                  <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                    <span>{m.fecha}</span>
                    <span className="inline-flex items-center gap-1">
                      <Paperclip className="size-3" />
                      {m.adjuntos_validos} CV{m.adjuntos_validos !== 1 ? "s" : ""}
                      {m.nombres_adjuntos.length > 0 && `: ${m.nombres_adjuntos.join(", ")}`}
                    </span>
                    <span>{MOTIVO[m.motivo] ?? m.motivo}</span>
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <select
                    aria-label={`Asignar ${m.asunto || m.message_id} a una búsqueda`}
                    className="min-h-10 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                    value={elegida[m.message_id] ?? ""}
                    onChange={(e) => setElegida((p) => ({ ...p, [m.message_id]: e.target.value }))}
                  >
                    <option value="">Elegí una búsqueda…</option>
                    {vacantes.map((v) => (
                      <option key={v.id} value={v.id}>{v.codigo} · {v.titulo}</option>
                    ))}
                  </select>
                  <Button
                    size="sm"
                    className="min-h-10"
                    disabled={!elegida[m.message_id] || m.adjuntos_validos === 0 || asignando === m.message_id}
                    onClick={() => asignar(m.message_id)}
                  >
                    {asignando === m.message_id ? "Asignando…" : "Asignar"}
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
