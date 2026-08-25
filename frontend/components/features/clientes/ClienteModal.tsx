"use client"

import { useEffect, useState } from "react"

import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { FieldError } from "@/components/ui/FieldError"
import { FormErrores } from "@/components/ui/FormErrores"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { mensajeDeError } from "@/components/features/clientes/erroresCliente"
import {
  guardarCliente, MAX_NOMBRE, type ErroresCliente,
} from "@/components/features/clientes/guardarCliente"
import type { Cliente } from "@/types/cliente"
import { avisarGuardado } from "@/components/features/shared/avisoGuardado"

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  cliente?: Cliente
}

/**
 * Alta y edición de un cliente. Un solo campo: el nombre.
 *
 * 🔴 NO HAY SELECTOR DE EMPRESA (migración 108). Un cliente no pertenece a ninguna, así que el
 * alta no tiene nada que elegir y el modal no lee el selector del sidebar. Antes había un
 * `<select>` acá y una validación "Requerido"; los dos desaparecieron con el campo.
 *
 * La validación y el envío viven en `guardarCliente.ts`, que es la ÚNICA puerta de esta pantalla
 * a los services de escritura. El porqué está en el encabezado de ese archivo (Radix monta por
 * portal y con vitest sin jsdom este componente no se puede testear).
 *
 * ⚠️ Este comentario NO escribe el nombre del service de alta, y no es casualidad: hay un test
 * estructural que verifica su ausencia en este archivo por substring, y un escáner de texto no
 * distingue un comentario de una llamada real. Nombrarlo acá volvería el test vacuo. Es el mismo
 * hueco que ya está documentado en `services/clientes.ts` con las rutas entre backticks.
 */
export function ClienteModal({ open, onClose, onSuccess, cliente }: Props) {
  const isEdit = Boolean(cliente)
  const [nombre, setNombre] = useState("")
  const [errores, setErrores] = useState<ErroresCliente>({})
  const [serverError, setServerError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setNombre(cliente?.nombre ?? "")
    setErrores({})
    setServerError("")
  }, [cliente, open])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setErrores({})
    setServerError("")
    try {
      const errs = await guardarCliente({ nombre }, cliente)
      if (errs) {
        setErrores(errs)
        return
      }
      avisarGuardado("Cliente", "m", isEdit)
      onSuccess()
    } catch (e2) {
      // El mensaje del backend se conserva: "Ya existe un cliente con ese nombre" le dice al
      // usuario qué hacer; un genérico lo deja tocando el botón. Ver erroresCliente.
      setServerError(mensajeDeError(e2))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      {/* El ancho (560px) y los campos de 34px los pone el patrón, no el modal: por eso ya no
          lleva `max-w-md`. */}
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar cliente" : "Nuevo cliente"}</DialogTitle>
          {/* 🔴 UNA LÍNEA QUE EXPLICA LA CONSECUENCIA, no lo que el modal es (§3). Lo que el
              usuario no puede deducir de un formulario de un solo campo es que el catálogo es
              GLOBAL —el cliente queda disponible para TODAS las empresas del grupo— y que el
              nombre es único en todo el sistema. */}
          <DialogDescription>
            {isEdit
              ? "El nombre es único en todo el sistema y el cambio se ve al instante en el link público de carga de horas."
              : "El cliente queda disponible para todas las empresas del grupo al cargar horas."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {/* El PRIMER nivel de la validación es la CUENTA; el "qué corrijo" lo contesta el
              segundo nivel, abajo del campo. */}
          <FormErrores cantidad={Object.values(errores).filter(Boolean).length} />
          <div className="space-y-1.5">
            <Label htmlFor="cliente-nombre">
              Nombre <span className="text-destructive" aria-hidden>*</span>
            </Label>
            <Input
              id="cliente-nombre"
              value={nombre}
              maxLength={MAX_NOMBRE}
              placeholder="Ej.: Acme S.A."
              aria-required
              aria-invalid={Boolean(errores.nombre)}
              onChange={(e) => setNombre(e.target.value)}
            />
            {errores.nombre && (
              <FieldError>{errores.nombre}</FieldError>
            )}
          </div>
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
