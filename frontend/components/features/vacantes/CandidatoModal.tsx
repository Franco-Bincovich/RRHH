"use client"

import { useState, useEffect } from "react"

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { FieldError } from "@/components/ui/FieldError"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { CvField } from "@/components/features/vacantes/CvField"
import { createCandidato } from "@/services/vacantes"
import type { CandidatoCreate } from "@/types/vacantes"

interface CandidatoModalProps {
  open: boolean
  vacanteId: string
  onClose: () => void
  onSuccess: () => void
}

type FormData = {
  nombre: string
  apellido: string
  email: string
  cargo_anterior: string
  empresa_anterior: string
}

type FormErrors = Partial<Record<keyof FormData, string>>

const EMPTY: FormData = {
  nombre: "",
  apellido: "",
  email: "",
  cargo_anterior: "",
  empresa_anterior: "",
}

function validate(form: FormData): FormErrors {
  const errors: FormErrors = {}
  if (!form.nombre.trim()) errors.nombre = "El nombre es requerido"
  if (!form.apellido.trim()) errors.apellido = "El apellido es requerido"
  if (!form.email.trim()) {
    errors.email = "El email es requerido"
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.email = "El email no es válido"
  }
  return errors
}

const TEXT_FIELDS: Array<{ field: keyof FormData; label: string; required?: boolean; type?: string }> = [
  { field: "nombre", label: "Nombre", required: true },
  { field: "apellido", label: "Apellido", required: true },
  { field: "email", label: "Email", required: true, type: "email" },
  { field: "cargo_anterior", label: "Cargo anterior" },
  { field: "empresa_anterior", label: "Empresa anterior" },
]

export function CandidatoModal({ open, vacanteId, onClose, onSuccess }: CandidatoModalProps) {
  const [form, setForm] = useState<FormData>(EMPTY)
  const [errors, setErrors] = useState<FormErrors>({})
  const [cvFile, setCvFile] = useState<File | null>(null)
  const [cvError, setCvError] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")

  useEffect(() => {
    if (!open) return
    setForm(EMPTY)
    setErrors({})
    setCvFile(null)
    setCvError("")
    setServerError("")
  }, [open])

  function field(key: keyof FormData) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value
      setForm((prev) => ({ ...prev, [key]: val }))
      if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate(form)
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    if (cvError) return
    setSubmitting(true)
    setServerError("")
    try {
      const payload: CandidatoCreate = {
        nombre: form.nombre.trim(),
        apellido: form.apellido.trim(),
        email: form.email.trim(),
        cargo_anterior: form.cargo_anterior.trim() || undefined,
        empresa_anterior: form.empresa_anterior.trim() || undefined,
      }
      await createCandidato(vacanteId, payload, cvFile)
      onSuccess()
    } catch {
      setServerError("Ocurrió un error al guardar. Intentá de nuevo.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Agregar candidato</DialogTitle>
        </DialogHeader>

        <form id="candidato-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">
            {TEXT_FIELDS.map(({ field: key, label, required, type }) => (
              <div key={key} className="flex flex-col gap-1.5">
                <Label htmlFor={key}>
                  {label}
                  {required && (
                    <span className="ml-0.5 text-destructive" aria-hidden>*</span>
                  )}
                </Label>
                <Input
                  id={key}
                  type={type ?? "text"}
                  value={form[key]}
                  onChange={field(key)}
                  aria-invalid={Boolean(errors[key])}
                  aria-required={required}
                />
                {errors[key] && (
                  <FieldError>{errors[key]}</FieldError>
                )}
              </div>
            ))}

            <CvField
              file={cvFile}
              error={cvError}
              onChange={(f, e) => { setCvFile(f); setCvError(e) }}
            />
          </div>

          {serverError && (
            <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>
          )}
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            className="min-h-11"
            onClick={onClose}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            form="candidato-form"
            className="min-h-11"
            disabled={submitting}
          >
            {submitting ? "Guardando..." : "Agregar candidato"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
