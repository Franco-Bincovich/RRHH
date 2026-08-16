"use client"

import { useEffect, useState } from "react"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { CamposEvento } from "@/components/features/eventos/CamposEvento"
import { mensajeDeError } from "@/components/features/eventos/erroresEvento"
import {
  guardarEvento, type ErroresEvento, type FormEvento,
} from "@/components/features/eventos/guardarEvento"
import type { Evento } from "@/types/evento"

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  evento?: Evento
}

const VACIO: FormEvento = {
  nombre: "", fecha: "", descripcion: "", diasAviso: "", esPublica: true,
}

/**
 * Alta y edición de un evento de agenda. SHELL: abrir, cerrar, submit y el error del servidor.
 * Los cinco campos viven en `CamposEvento.tsx` — el corte se hizo cuando este archivo llegó a
 * 178 líneas contra el límite de 150.
 *
 * La validación y el envío viven en `guardarEvento.ts`, que es la ÚNICA puerta de esta pantalla
 * a los services de escritura: `Dialog` de Radix monta por PORTAL y con vitest sin jsdom
 * `renderToStaticMarkup` de este componente devuelve "", así que un test de acá pasaría con el
 * formulario entero borrado. Molde y porqué completo: `clientes/ClienteModal.tsx`.
 *
 * ⚠️ Este comentario NO escribe el nombre del service de alta: hay un test estructural que
 * verifica por substring que este archivo no lo nombre, y un escáner de texto no distingue un
 * comentario de una llamada real.
 */
export function EventoModal({ open, onClose, onSuccess, evento }: Props) {
  const isEdit = Boolean(evento)
  const [form, setForm] = useState<FormEvento>(VACIO)
  const [errores, setErrores] = useState<ErroresEvento>({})
  const [serverError, setServerError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  // El borrador se resincroniza al abrir y al cambiar de evento, así lo que se ve es lo que está
  // persistido y no lo que quedó tipeado la vez anterior.
  useEffect(() => {
    setForm(evento
      ? {
        nombre: evento.nombre,
        fecha: evento.fecha,
        descripcion: evento.descripcion ?? "",
        diasAviso: String(evento.dias_aviso),
        esPublica: evento.es_publica,
      }
      : VACIO)
    setErrores({})
    setServerError("")
  }, [evento, open])

  const campo = <K extends keyof FormEvento>(k: K, v: FormEvento[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setErrores({})
    setServerError("")
    try {
      const errs = await guardarEvento(form, evento)
      if (errs) {
        setErrores(errs)
        return
      }
      onSuccess()
    } catch (e2) {
      setServerError(mensajeDeError(e2))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar evento" : "Nuevo evento"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <CamposEvento form={form} errores={errores} onCampo={campo} />
          {serverError && <p className="text-sm text-destructive">{serverError}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" className="min-h-11"
                    onClick={onClose} disabled={submitting}>
              Cancelar
            </Button>
            <Button type="submit" className="min-h-11" disabled={submitting}>
              {submitting ? "Guardando..." : isEdit ? "Guardar" : "Crear"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
