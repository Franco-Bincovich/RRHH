"use client"

import { useEffect, useState } from "react"
import { TriangleAlert } from "lucide-react"

import { avisarGuardado } from "@/components/features/shared/avisoGuardado"
import { Button } from "@/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { updateVacante } from "@/services/vacantes"

import { normalizarCodigo, validarCodigo } from "./codigoVacante"
import { VacanteCampoCodigo } from "./VacanteCampoCodigo"

/**
 * Corregir el código de una búsqueda que ya existe.
 *
 * 🔴 SE PUEDE EDITAR, Y NO ES UNA CONCESIÓN: el caso que lo motiva es un typo en el código que YA
 * se pegó en el aviso. Bloquear la edición dejaría a Capital Humano sin ninguna salida salvo
 * borrar la búsqueda y volver a crearla — que se lleva los candidatos por delante.
 *
 * 🔴 QUÉ PASA CON LOS CVs QUE YA ENTRARON: NADA. Un candidato cuelga de `vacante_id`, no del
 * código, así que cambiarlo no mueve ni desasocia a nadie. Lo que queda desalineado es el AVISO
 * PUBLICADO: un mail que llegue con el código viejo ya no matchea y cae en "Mails pendientes"
 * con motivo `vacante_desconocida`, desde donde se asigna a mano. No se pierde nada; hay trabajo
 * manual hasta que el aviso se actualice.
 *
 * Por eso el aviso ámbar aparece SÓLO cuando la búsqueda ya tiene candidatos: es la señal de que
 * el código está circulando de verdad. Con cero candidatos, cambiarlo no tiene ninguna
 * consecuencia y un cartel ahí sería ruido que enseña a ignorar los carteles.
 *
 * ⚠️ NO se usa `ConfirmDialog`: éste no es un borrado ni una acción de un click — es un
 * formulario con un campo, y la confirmación es apretar Guardar. El aviso vive DENTRO del modal,
 * arriba del campo, que es donde se lee antes de escribir.
 */
export function EditarCodigoModal({ open, vacanteId, codigoActual, candidatos, onClose, onSaved }: {
  open: boolean
  vacanteId: string
  codigoActual: string
  /** Cuántos candidatos tiene ya la búsqueda. Decide si se muestra el aviso. */
  candidatos: number
  onClose: () => void
  onSaved: () => void
}) {
  const [codigo, setCodigo] = useState(codigoActual)
  const [error, setError] = useState<string | undefined>(undefined)
  const [serverError, setServerError] = useState("")
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    if (!open) return
    setCodigo(codigoActual)
    setError(undefined)
    setServerError("")
  }, [open, codigoActual])

  const sinCambio = normalizarCodigo(codigo) === codigoActual.toUpperCase()

  async function guardar(e: React.FormEvent) {
    e.preventDefault()
    const problema = validarCodigo(codigo)
    if (problema) {
      setError(problema)
      return
    }
    setGuardando(true)
    setServerError("")
    try {
      await updateVacante(vacanteId, { codigo: normalizarCodigo(codigo) })
      avisarGuardado("Código", "m", true)
      onSaved()
    } catch (err) {
      // El mensaje del backend nombra la búsqueda que ya tiene ese código: es lo único que
      // permite resolverlo. Ver el mismo comentario en VacanteModal.
      setServerError(err instanceof Error ? err.message : "No se pudo guardar el código.")
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>Cambiar el código de la búsqueda</DialogTitle>
          <DialogDescription>
            Es lo que los candidatos escriben en el asunto del mail para que su CV entre solo.
          </DialogDescription>
        </DialogHeader>

        <form id="codigo-form" onSubmit={guardar} noValidate>
          {candidatos > 0 && (
            <div
              role="alert"
              className="mb-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200"
            >
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              <p>
                Esta búsqueda ya recibió {candidatos} {candidatos === 1 ? "candidato" : "candidatos"}.
                Los que ya entraron NO se pierden ni se mueven. Pero los mails que lleguen con{" "}
                <strong>{codigoActual}</strong> van a dejar de asignarse solos y van a quedar en
                &quot;Mails pendientes&quot; para asignar a mano: si el aviso ya está publicado,
                actualizalo también.
              </p>
            </div>
          )}

          <VacanteCampoCodigo
            value={codigo}
            error={error}
            ayuda={false}
            onChange={(e) => { setCodigo(e.target.value); setError(undefined) }}
          />

          {serverError && (
            <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>
          )}
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={guardando}>
            Cancelar
          </Button>
          <Button type="submit" form="codigo-form" className="min-h-11" disabled={guardando || sinCambio}>
            {guardando ? "Guardando..." : "Guardar código"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
