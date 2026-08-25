"use client"

import { useEffect, useState } from "react"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ObjetivoFormFields } from "@/components/features/objetivos/ObjetivoFormFields"
import type { FormData, FormErrors } from "@/components/features/objetivos/ObjetivoFormFields"
import { createObjetivo, fetchObjetivos, fetchUsuariosActivos, updateObjetivo } from "@/services/objetivos"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Objetivo, ObjetivoCreate, ObjetivoUpdate, UserItem } from "@/types/objetivo"
import type { Empresa } from "@/types/empresa"
import { avisarGuardado } from "@/components/features/shared/avisoGuardado"

interface Props { open: boolean; onClose: () => void; onSuccess: () => void; editing?: Objetivo | null }

const EMPTY: FormData = { empresa_id: "", responsable_id: "", titulo: "", descripcion: "", prioridad: "media", fecha_entrega: "", parent_id: "", responsables: [] }

function validate(form: FormData, isEdit: boolean): FormErrors {
  const e: FormErrors = {}
  if (!isEdit && !form.empresa_id) e.empresa_id = "Requerido"
  if (!form.responsable_id)        e.responsable_id = "Requerido"
  if (!form.titulo.trim())         e.titulo = "Requerido"
  return e
}

export function ObjetivoModal({ open, onClose, onSuccess, editing }: Props) {
  const isEdit = Boolean(editing)
  const [form, setForm]             = useState<FormData>(EMPTY)
  const [errors, setErrors]         = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")
  const [empresas, setEmpresas]     = useState<Empresa[]>([])
  const [usuarios, setUsuarios]     = useState<UserItem[]>([])
  const [padres, setPadres]         = useState<Objetivo[]>([])

  useEffect(() => {
    if (!open) return
    setErrors({}); setServerError("")
    if (editing) {
      setForm({
        empresa_id: editing.empresa_id, responsable_id: editing.responsable_id,
        titulo: editing.titulo, descripcion: editing.descripcion ?? "",
        prioridad: editing.prioridad, fecha_entrega: editing.fecha_entrega ?? "",
        parent_id: editing.parent_id ?? "",
        // El dueño queda fuera de la lista editable: el backend lo agrega siempre, y
        // ofrecerlo como checkbox dejaría destildarlo, que es un estado imposible.
        responsables: editing.responsables.map((r) => r.id).filter((id) => id !== editing.responsable_id),
      })
    } else {
      setForm({ ...EMPTY, empresa_id: getEmpresaActivaId() ?? "" })
    }
  }, [open, editing])

  useEffect(() => {
    if (!open) return
    fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
    fetchUsuariosActivos().then((r) => setUsuarios(r.items)).catch(() => {})
    // 🔴 Candidatos a padre: el listado ya devuelve SOLO raíces, así que basta con sacar el
    // objetivo que se está editando (nadie puede ser su propio padre). Un objetivo que ya
    // tiene hijos tampoco puede colgarse de otro, pero eso lo rechaza el backend con un 422
    // legible: filtrarlo acá además duplicaría la regla de profundidad en dos lugares.
    fetchObjetivos().then((r) => setPadres(r.items.filter((o) => o.id !== editing?.id)))
      .catch(() => {})
  }, [open, editing])

  function field(key: keyof FormData) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      setForm((p) => ({ ...p, [key]: e.target.value }))
      if (errors[key]) setErrors((p) => ({ ...p, [key]: undefined }))
    }
  }

  function toggleResponsable(id: string) {
    setForm((p) => ({
      ...p,
      responsables: p.responsables.includes(id)
        ? p.responsables.filter((r) => r !== id)
        : [...p.responsables, id],
    }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate(form, isEdit)
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setSubmitting(true); setServerError("")
    try {
      if (isEdit && editing) {
        const payload: ObjetivoUpdate = {
          responsable_id: form.responsable_id || undefined,
          titulo: form.titulo.trim() || undefined,
          descripcion: form.descripcion.trim() || undefined,
          prioridad: form.prioridad,
          fecha_entrega: form.fecha_entrega || undefined,
          parent_id: form.parent_id || undefined,
          responsables: form.responsables,
        }
        await updateObjetivo(editing.id, payload)
      } else {
        const payload: ObjetivoCreate = {
          empresa_id: form.empresa_id, responsable_id: form.responsable_id,
          titulo: form.titulo.trim(), prioridad: form.prioridad,
          descripcion: form.descripcion.trim() || undefined,
          fecha_entrega: form.fecha_entrega || undefined,
          parent_id: form.parent_id || undefined,
          responsables: form.responsables,
        }
        await createObjetivo(payload)
      }
      avisarGuardado("Objetivo", "m", isEdit)
      onSuccess()
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Ocurrió un error al guardar")
    } finally { setSubmitting(false) }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>{isEdit ? "Editar objetivo" : "Nuevo objetivo"}</DialogTitle></DialogHeader>
        <form id="obj-form" onSubmit={handleSubmit} noValidate>
          <ObjetivoFormFields
            form={form} errors={errors} empresas={empresas} usuarios={usuarios}
            padres={padres} isEdit={isEdit} field={field}
            onToggleResponsable={toggleResponsable}
          />
          {serverError && <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>}
        </form>
        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>Cancelar</Button>
          <Button type="submit" form="obj-form" className="min-h-11" disabled={submitting}>
            {submitting ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear objetivo"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
