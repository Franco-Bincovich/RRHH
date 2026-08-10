"use client"

import { useEffect, useState } from "react"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { createCliente, updateCliente } from "@/services/clientes"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { mensajeDeError } from "@/components/features/clientes/erroresCliente"
import type { Cliente } from "@/types/cliente"

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  cliente?: Cliente
}

export const MAX_NOMBRE = 120

/** Error de nombre, o "" si está bien. Exportada para testearla sin DOM (vitest sin jsdom). */
export function validarNombre(nombre: string): string {
  if (!nombre.trim()) return "El nombre es requerido"
  if (nombre.trim().length > MAX_NOMBRE) return `Máximo ${MAX_NOMBRE} caracteres`
  return ""
}

export function ClienteModal({ open, onClose, onSuccess, cliente }: Props) {
  const isEdit = Boolean(cliente)
  const [nombre, setNombre] = useState("")
  const [error, setError] = useState("")
  const [serverError, setServerError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setNombre(cliente?.nombre ?? "")
    setError("")
    setServerError("")
  }, [cliente, open])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const err = validarNombre(nombre)
    setError(err)
    if (err) return
    setSubmitting(true)
    setServerError("")
    try {
      // La empresa NO es editable: en el alta sale de la empresa activa y en la edición no viaja.
      if (cliente) await updateCliente(cliente.id, { nombre: nombre.trim() })
      else await createCliente({ empresa_id: getEmpresaActivaId() ?? "", nombre: nombre.trim() })
      onSuccess()
    } catch (e2) {
      // El mensaje del backend se conserva: "Ya existe un cliente con ese nombre en la empresa"
      // le dice al usuario qué hacer; un genérico lo deja tocando el botón. Ver erroresCliente.
      setServerError(mensajeDeError(e2))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar cliente" : "Nuevo cliente"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="cliente-nombre">Nombre</Label>
            <Input
              id="cliente-nombre"
              value={nombre}
              maxLength={MAX_NOMBRE}
              placeholder="Ej.: Acme S.A."
              onChange={(e) => setNombre(e.target.value)}
            />
            {error && <p className="text-sm text-destructive">{error}</p>}
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
