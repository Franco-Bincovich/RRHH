"use client"

import { useEffect, useState } from "react"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { FormErrores } from "@/components/ui/FormErrores"
import type { CamposPerfilResponse, PerfilPuesto } from "@/types/perfilPuesto"

import { PerfilFormCampos } from "./PerfilFormCampos"
import { valoresIniciales } from "./_perfilCampos"
import { guardarPerfil, mensajeDeError, type ErroresPerfil } from "./guardarPerfil"

/**
 * Alta y edición de un perfil de puesto.
 *
 * Este archivo es SOLO la caja: título, pie y el manejo del envío. Los campos los dibuja
 * `PerfilFormCampos` a partir de lo que devuelve el endpoint `/campos`, y la validación y el
 * envío viven en `guardarPerfil.ts`. El corte no es estético: el `Dialog` monta por PORTAL, así
 * que con vitest sin jsdom este componente renderiza a `""` — todo lo que haya que poder
 * desmentir tiene que estar afuera. Molde: `ClienteModal` + `guardarCliente`.
 *
 * 🔴 NO HAY SELECTOR DE EMPRESA, y su ausencia es la decisión de fondo del módulo: un perfil es
 * del GRUPO (migración 113). El alta no tiene empresa que elegir, el modal no lee el selector del
 * sidebar y ninguna de las tres escrituras manda `X-Empresa-Id`.
 */
export function PerfilModal({
  open, onClose, onSuccess, catalogos, perfil,
}: {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  catalogos: CamposPerfilResponse
  perfil?: PerfilPuesto
}) {
  const isEdit = Boolean(perfil)
  const [valores, setValores] = useState<Record<string, string>>({})
  const [errores, setErrores] = useState<ErroresPerfil>({})
  const [serverError, setServerError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  // Se re-siembra al abrir y al cambiar de perfil: sin esto, editar uno y después abrir el alta
  // mostraría el formulario con los datos del anterior.
  useEffect(() => {
    setValores(valoresIniciales(catalogos.campos, perfil))
    setErrores({})
    setServerError("")
  }, [catalogos, perfil, open])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setErrores({})
    setServerError("")
    try {
      const errs = await guardarPerfil(valores, catalogos.campos, perfil)
      if (errs) {
        setErrores(errs)
        return
      }
      onSuccess()
    } catch (e2) {
      // El mensaje del backend se conserva: el 409 explica que el nombre es único en TODO el
      // sistema y no por empresa, que es lo que hace falta para resolverlo. Ver `guardarPerfil`.
      setServerError(mensajeDeError(e2))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      {/* Sin `max-h` ni `overflow` propios: la altura y el scroll los decide el primitivo, y hay
          un barrido que lo verifica. Este formulario tiene 12 campos y scrollea de verdad. */}
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar perfil de puesto" : "Nuevo perfil de puesto"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} noValidate className="space-y-5">
          <FormErrores cantidad={Object.keys(errores).length} />
          <PerfilFormCampos
            catalogos={catalogos}
            valores={valores}
            errores={errores}
            onChange={(campo, valor) => setValores((v) => ({ ...v, [campo]: valor }))}
          />
          {serverError && <p className="text-sm text-destructive" role="alert">{serverError}</p>}
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
