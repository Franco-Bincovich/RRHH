"use client"

import { useEffect, useState } from "react"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { mensajeDeError } from "@/components/features/clientes/erroresCliente"
import {
  guardarCliente, MAX_NOMBRE, type ErroresCliente,
} from "@/components/features/clientes/guardarCliente"
import type { Cliente } from "@/types/cliente"
import type { Empresa } from "@/types/empresa"

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  cliente?: Cliente
}

const SEL = "h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:opacity-50"

/**
 * Alta y edición de un cliente.
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
  const [empresaId, setEmpresaId] = useState("")
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [errores, setErrores] = useState<ErroresCliente>({})
  const [serverError, setServerError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setNombre(cliente?.nombre ?? "")
    // Preseleccionada con la empresa activa: con una empresa elegida en el sidebar el alta sigue
    // siendo un solo click. En modo consolidado queda "" y la validación lo frena — que es la
    // diferencia con el bug: antes ese "" salía a la red y volvía como 422.
    setEmpresaId(cliente?.empresa_id ?? getEmpresaActivaId() ?? "")
    setErrores({})
    setServerError("")
  }, [cliente, open])

  useEffect(() => {
    // Solo en el alta: `empresa_id` no es editable, así que en la edición el select no se muestra
    // y pedir el listado sería una ida a la red para llenar un control que no existe.
    if (!open || isEdit) return
    fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [open, isEdit])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setErrores({})
    setServerError("")
    try {
      const errs = await guardarCliente({ nombre, empresaId }, cliente)
      if (errs) {
        setErrores(errs)
        return
      }
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
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {!isEdit && (
            <div className="space-y-1.5">
              <Label htmlFor="cliente-empresa">
                Empresa <span className="text-destructive" aria-hidden>*</span>
              </Label>
              <select
                id="cliente-empresa"
                className={SEL}
                value={empresaId}
                aria-required
                aria-invalid={Boolean(errores.empresa)}
                onChange={(e) => setEmpresaId(e.target.value)}
              >
                <option value="">Seleccionar empresa</option>
                {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
              </select>
              {errores.empresa && (
                <p className="text-sm text-destructive" role="alert">{errores.empresa}</p>
              )}
            </div>
          )}
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
              <p className="text-sm text-destructive" role="alert">{errores.nombre}</p>
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
