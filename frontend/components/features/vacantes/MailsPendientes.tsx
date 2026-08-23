"use client"

import { useCallback, useEffect, useState } from "react"
import { Inbox } from "lucide-react"

import { Button } from "@/components/ui/button"
import { MailPendienteFila } from "@/components/features/vacantes/MailPendienteFila"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { mensajeDeCasilla, vista } from "@/components/features/vacantes/_mailsPendientes"
import { asignarMail, fetchMailsPendientes, fetchVacantes } from "@/services/vacantes"
import type { Vacante } from "@/types/vacantes"
import type { MailPendiente } from "@/types/vacantesIngesta"

/**
 * Los mails de la casilla que no matchearon ninguna búsqueda, con el selector para asignarlos.
 *
 * 🔴 NO HAY ESTADO PERSISTIDO: la lista se relee de Gmail cada vez. La casilla es la fuente de
 * verdad, así que no hay dos estados que sincronizar. Un mail asignado desaparece solo —al crear
 * el candidato se guarda su `gmail_message_id` y la lectura siguiente lo saltea—, y para
 * descartar uno sin asignarlo RRHH lo archiva o etiqueta EN GMAIL. Por eso acá no hay botón de
 * "descartar": sería un segundo estado del que el buzón no se entera.
 *
 * 🔴 Y POR ESO MISMO, CUANDO LA CASILLA NO SE PUEDE LEER NO HAY NADA QUE AFIRMAR SOBRE EL BUZÓN.
 * Hasta el 23/8/2026 este bloque mostraba el error Y debajo "No hay mails con adjuntos esperando
 * asignación": con la casilla caída le decía a RRHH que no había nada, teniendo mails de verdad
 * esperando. La decisión de qué se muestra vive en `_mailsPendientes.ts`, donde se puede testear.
 *
 * Orquestador: la carga, los dos errores y qué se muestra. La tarjeta de cada mail está en
 * `MailPendienteFila.tsx`.
 */
export function MailsPendientes() {
  const [mails, setMails] = useState<MailPendiente[]>([])
  const [vacantes, setVacantes] = useState<Vacante[]>([])
  const [elegida, setElegida] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [asignando, setAsignando] = useState<string | null>(null)
  // 🔴 DOS errores y no uno: "no se pudo leer la casilla" invalida el bloque entero, "no se pudo
  // asignar ESE mail" no invalida nada — la lista que se está viendo sigue siendo buena. Con un
  // solo estado, un fallo al asignar se llevaría puesta la lista.
  const [errorCasilla, setErrorCasilla] = useState<string | null>(null)
  const [errorAsignar, setErrorAsignar] = useState<string | null>(null)

  const cargar = useCallback(async () => {
    setLoading(true)
    setErrorCasilla(null)
    setErrorAsignar(null)
    try {
      // ⚠️ Es un SELECTOR, no un listado: necesita todas las vacantes elegibles, así que pide
      // el tope del endpoint (100, el `le` del router). Si alguna vez hay más de 100 abiertas,
      // esto pasa a ser un combobox con búsqueda server-side, no un `page_size` más grande.
      const [m, v] = await Promise.all([fetchMailsPendientes(), fetchVacantes(undefined, undefined, 1, 100)])
      setMails(m)
      setVacantes(v.items)
    } catch (err) {
      setErrorCasilla(mensajeDeCasilla(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  async function asignar(messageId: string) {
    const vacanteId = elegida[messageId]
    if (!vacanteId) return
    setAsignando(messageId)
    setErrorAsignar(null)
    try {
      await asignarMail(messageId, vacanteId)
      // Se saca de la lista sin recargar: el backend ya lo va a saltear en la próxima lectura.
      setMails((prev) => prev.filter((m) => m.message_id !== messageId))
    } catch (err) {
      setErrorAsignar(err instanceof Error ? err.message : "No se pudo asignar el mail.")
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

      {errorAsignar && <p className="mb-3 text-sm text-destructive" role="alert">{errorAsignar}</p>}

      {vista(errorCasilla, mails.length) === "error" ? (
        // El `description` es el mensaje del backend TAL CUAL: es el único que sabe si hay que
        // reconectar la cuenta de Google o esperar un rato. Ver `_mailsPendientes.ts`.
        <ErrorState
          title="No se pudo leer la casilla"
          description={errorCasilla ?? undefined}
          action={cargar}
        />
      ) : vista(errorCasilla, mails.length) === "vacio" ? (
        <EmptyState
          icon={<Inbox />}
          title="No hay mails sin asignar"
          description="Los mails con CV que traen el código de la búsqueda en el asunto se procesan solos."
        />
      ) : (
        <div className="space-y-2">
          {mails.map((m) => (
            <MailPendienteFila
              key={m.message_id}
              mail={m}
              vacantes={vacantes}
              elegida={elegida[m.message_id] ?? ""}
              asignando={asignando === m.message_id}
              onElegir={(id) => setElegida((p) => ({ ...p, [m.message_id]: id }))}
              onAsignar={() => asignar(m.message_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
