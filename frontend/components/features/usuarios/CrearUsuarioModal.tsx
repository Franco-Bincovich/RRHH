"use client"

import { useEffect, useState } from "react"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { FormErrores } from "@/components/ui/FormErrores"
import { AVISO_PASSWORD_UNICA } from "@/components/features/usuarios/_avisos"
import { EmpleadoLiderSelect } from "@/components/features/usuarios/EmpleadoLiderSelect"
import { SelectField, TextField } from "@/components/features/usuarios/_fields"
// La forma del formulario y su validación viven afuera, en un módulo puro. El porqué del corte
// está en el encabezado de ese archivo.
import {
  EMPTY, ROL_OPTIONS, validate, type FormData, type FormErrors,
} from "@/components/features/usuarios/_crearUsuarioForm"
import { useEmpleadosPorRol } from "@/hooks/useEmpleadosPorRol"
import { crearUsuario, type CrearUsuarioPayload, type CrearUsuarioResult } from "@/services/usuarios"

interface CrearUsuarioModalProps {
  open: boolean
  onClose: () => void
  onCreated: (result: CrearUsuarioResult) => void
}

export function CrearUsuarioModal({ open, onClose, onCreated }: CrearUsuarioModalProps) {
  const [form, setForm] = useState<FormData>(EMPTY)
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")
  const { empleados, loading: empLoading, error: empError, reload } = useEmpleadosPorRol(open, form.rol)

  useEffect(() => {
    if (!open) return
    setForm(EMPTY)
    setErrors({})
    setServerError("")
  }, [open])

  function field(key: keyof FormErrors) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value
      setForm((p) => ({ ...p, [key]: val }))
      if (errors[key]) setErrors((p) => ({ ...p, [key]: undefined }))
    }
  }

  // Al cambiar el rol se resetea el vínculo: la lista de empleados cambia (líderes ↔ todos).
  const handleRol = (rol: string) => setForm((p) => ({ ...p, rol, empleadoId: "" }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate(form)
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setSubmitting(true)
    setServerError("")
    try {
      const payload: CrearUsuarioPayload = {
        nombre: form.nombre.trim(),
        apellido: form.apellido.trim(),
        email: form.email.trim(),
        username: form.username.trim(),
        rol: form.rol,
        empleado_id: form.empleadoId || undefined,
      }
      onCreated(await crearUsuario(payload))
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "No se pudo crear el usuario. Intentá de nuevo.")
    } finally {
      setSubmitting(false)
    }
  }

  const hint = form.rol === "mandos_medios"
    ? "Opcional. Solo se listan colaboradores marcados como líderes."
    : "Opcional. Se listan todos los colaboradores activos."

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      {/* El ancho (560px) y los campos de 34px los pone el patrón, no el modal: por eso ya no
          lleva `max-w-lg`. */}
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>Crear usuario</DialogTitle>
          {/* La línea que explica la CONSECUENCIA (§3). El texto y su porqué viven en
              `_avisos.ts`: es una afirmación sobre el sistema, no una decoración del modal. */}
          <DialogDescription>{AVISO_PASSWORD_UNICA}</DialogDescription>
        </DialogHeader>

        <form id="crear-usuario-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">
            {/* El PRIMER nivel de la validación es la CUENTA, no la lista de campos: el "qué
                corrijo" lo contesta el segundo nivel, en cada campo. */}
            <FormErrores cantidad={Object.values(errors).filter(Boolean).length} />
            <div className="grid grid-cols-2 gap-4">
              <TextField id="nombre" label="Nombre" value={form.nombre} onChange={field("nombre")} error={errors.nombre} />
              <TextField id="apellido" label="Apellido" value={form.apellido} onChange={field("apellido")} error={errors.apellido} />
            </div>
            <TextField id="email" label="Email" type="email" value={form.email} onChange={field("email")} error={errors.email} />
            <TextField id="username" label="Nombre de usuario" value={form.username} onChange={field("username")} error={errors.username} />
            <SelectField id="rol" label="Rol" value={form.rol} onChange={handleRol} options={ROL_OPTIONS} />
            <EmpleadoLiderSelect
              value={form.empleadoId}
              onChange={(id) => setForm((p) => ({ ...p, empleadoId: id }))}
              options={empleados}
              loading={empLoading}
              error={empError}
              onRetry={reload}
              hint={hint}
            />
          </div>
          {serverError && <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>}
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="submit" form="crear-usuario-form" className="min-h-11" disabled={submitting}>
            {submitting ? "Creando..." : "Crear usuario"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
