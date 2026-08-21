"use client"

import { useEffect, useState } from "react"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { AvisoImpacto } from "@/components/ui/AvisoImpacto"
import { Button } from "@/components/ui/button"
import { FormErrores } from "@/components/ui/FormErrores"
import type { Recategorizacion } from "@/types/recategorizacion"

import { RecategorizacionForm } from "./RecategorizacionForm"
import { TEXTO_AVISO_RETROACTIVO, avisoRetroactivo } from "./_retroactiva"
import {
  formInicial, guardarRecategorizacion, mensajeDeError,
  type ErroresRecategorizacion, type FormRecategorizacion,
} from "./guardarRecategorizacion"
import { useUltimaRecategorizacion } from "./useUltimaRecategorizacion"

/**
 * Alta y edición de una recategorización.
 *
 * Este archivo es SOLO la caja: título, aviso, pie y el manejo del envío. Los campos los dibuja
 * `RecategorizacionForm` y la validación vive en `guardarRecategorizacion.ts` — el `Dialog` monta
 * por portal y con vitest sin jsdom renderiza a `""`, así que nada verificable puede vivir acá.
 *
 * 🔴 EL AVISO DE FECHA RETROACTIVA VA EN EL PIE, EN ÁMBAR, Y APARECE MIENTRAS SE ELIGE LA FECHA.
 * No es una validación —la operación es legítima y se guarda igual— sino una consecuencia real de
 * apretar Guardar que el usuario no puede deducir de lo que ve: con una fecha anterior a la
 * última recategorización de esa persona, el histórico se registra pero **el legajo no cambia**.
 * Va sobre el pie porque el cuerpo scrollea y un aviso ahí adentro desaparece justo en el
 * formulario largo, que es este. La regla en sí está en `_retroactiva.ts`.
 *
 * 🔴 NO HAY BOTÓN DE BORRAR. El backend no publica DELETE: borrar rompería la cadena de valores
 * anteriores. La corrección de una fila mal cargada es editarla, que es lo que este mismo modal
 * hace.
 */
export function RecategorizacionModal({
  open, onClose, onSuccess, original, mostrarImpacto,
}: {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  original?: Recategorizacion
  mostrarImpacto: boolean
}) {
  const isEdit = Boolean(original)
  const [form, setForm] = useState<FormRecategorizacion>(() => formInicial(original))
  const [errores, setErrores] = useState<ErroresRecategorizacion>({})
  const [serverError, setServerError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  // Se re-siembra al abrir y al cambiar de fila: sin esto, editar una y después abrir el alta
  // mostraría el formulario con los datos de la anterior.
  useEffect(() => {
    setForm(formInicial(original))
    setErrores({})
    setServerError("")
  }, [original, open])

  const ultima = useUltimaRecategorizacion(form.empleadoId, open)
  const retroactiva = avisoRetroactivo(form.fechaEfectiva, ultima)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setErrores({})
    setServerError("")
    try {
      const errs = await guardarRecategorizacion(form, original)
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
      {/* Sin `max-h` ni `overflow` propios: la altura y el scroll los decide el primitivo. */}
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Editar recategorización" : "Registrar recategorización"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <FormErrores cantidad={Object.keys(errores).length} />
          <RecategorizacionForm
            form={form}
            errores={errores}
            original={original}
            mostrarImpacto={mostrarImpacto}
            onChange={(campo, valor) => setForm((f) => ({ ...f, [campo]: valor }))}
            onEmpleadoChange={(emp) => setForm((f) => ({ ...f, empleadoId: emp?.id ?? "" }))}
          />
          {serverError && <p className="text-sm text-destructive" role="alert">{serverError}</p>}
          <DialogFooter aviso={retroactiva ? <AvisoImpacto>{TEXTO_AVISO_RETROACTIVO}</AvisoImpacto> : undefined}>
            <Button type="button" variant="outline" className="min-h-11"
                    onClick={onClose} disabled={submitting}>
              Cancelar
            </Button>
            <Button type="submit" className="min-h-11" disabled={submitting}>
              {submitting ? "Guardando..." : isEdit ? "Guardar" : "Registrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
