"use client"

import { useEffect, useState } from "react"
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { createCapacitacion, updateCapacitacion } from "@/services/capacitaciones"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Capacitacion, CapacitacionCreate, CapacitacionUpdate } from "@/types/capacitacion"
import type { Empresa } from "@/types/empresa"

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  editing?: Capacitacion | null
}

type FormData = {
  empresa_id: string
  nombre: string
  descripcion: string
  categoria: string
  duracion_horas: string
  obligatoria: boolean
}

type FormErrors = Partial<Record<keyof FormData, string>>

const EMPTY: FormData = {
  empresa_id: "", nombre: "", descripcion: "", categoria: "", duracion_horas: "", obligatoria: false,
}

const SEL =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:opacity-50"

function validate(form: FormData): FormErrors {
  const e: FormErrors = {}
  if (!form.empresa_id) e.empresa_id = "Requerido"
  if (!form.nombre.trim()) e.nombre = "Requerido"
  if (form.duracion_horas && isNaN(Number(form.duracion_horas))) e.duracion_horas = "Debe ser un número"
  return e
}

export function CapacitacionModal({ open, onClose, onSuccess, editing }: Props) {
  const [form, setForm] = useState<FormData>(EMPTY)
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const isEditing = Boolean(editing)

  useEffect(() => {
    if (!open) return
    setErrors({})
    setServerError("")
    if (editing) {
      setForm({
        empresa_id: editing.empresa_id,
        nombre: editing.nombre,
        descripcion: editing.descripcion ?? "",
        categoria: editing.categoria ?? "",
        duracion_horas: editing.duracion_horas != null ? String(editing.duracion_horas) : "",
        obligatoria: editing.obligatoria,
      })
    } else {
      setForm({ ...EMPTY, empresa_id: getEmpresaActivaId() ?? "" })
    }
  }, [open, editing])

  useEffect(() => {
    if (!open) return
    fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [open])

  function field(key: keyof FormData) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      setForm((p) => ({ ...p, [key]: e.target.value }))
      if (errors[key]) setErrors((p) => ({ ...p, [key]: undefined }))
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate(form)
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setSubmitting(true)
    setServerError("")
    try {
      if (isEditing) {
        const payload: CapacitacionUpdate = {
          nombre: form.nombre.trim(),
          descripcion: form.descripcion.trim() || undefined,
          categoria: form.categoria.trim() || undefined,
          duracion_horas: form.duracion_horas ? Number(form.duracion_horas) : undefined,
          obligatoria: form.obligatoria,
        }
        await updateCapacitacion(editing!.id, payload)
      } else {
        const payload: CapacitacionCreate = {
          empresa_id: form.empresa_id,
          nombre: form.nombre.trim(),
          descripcion: form.descripcion.trim() || undefined,
          categoria: form.categoria.trim() || undefined,
          duracion_horas: form.duracion_horas ? Number(form.duracion_horas) : undefined,
          obligatoria: form.obligatoria,
        }
        await createCapacitacion(payload)
      }
      onSuccess()
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Ocurrió un error al guardar")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Editar formación" : "Nueva formación"}</DialogTitle>
        </DialogHeader>

        <form id="cap-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">

            {!isEditing && (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="cap_empresa_id">Empresa <span className="text-destructive" aria-hidden>*</span></Label>
                <select id="cap_empresa_id" className={SEL} value={form.empresa_id} onChange={field("empresa_id")} aria-required aria-invalid={Boolean(errors.empresa_id)}>
                  <option value="">Seleccionar empresa</option>
                  {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
                </select>
                {errors.empresa_id && <p className="text-xs text-destructive" role="alert">{errors.empresa_id}</p>}
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="cap_nombre">Nombre <span className="text-destructive" aria-hidden>*</span></Label>
              <Input id="cap_nombre" value={form.nombre} onChange={field("nombre")} aria-required aria-invalid={Boolean(errors.nombre)} placeholder="ej. Seguridad informática" />
              {errors.nombre && <p className="text-xs text-destructive" role="alert">{errors.nombre}</p>}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="cap_categoria">Categoría <span className="text-muted-foreground text-xs font-normal">(opcional)</span></Label>
                <Input id="cap_categoria" value={form.categoria} onChange={field("categoria")} placeholder="ej. Compliance" />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="cap_horas">Duración (hs) <span className="text-muted-foreground text-xs font-normal">(opcional)</span></Label>
                <Input id="cap_horas" type="number" min="0" step="0.5" value={form.duracion_horas} onChange={field("duracion_horas")} placeholder="ej. 8" aria-invalid={Boolean(errors.duracion_horas)} />
                {errors.duracion_horas && <p className="text-xs text-destructive" role="alert">{errors.duracion_horas}</p>}
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="cap_desc">Descripción <span className="text-muted-foreground text-xs font-normal">(opcional)</span></Label>
              <Textarea id="cap_desc" value={form.descripcion} onChange={field("descripcion")} rows={2} className="resize-none" placeholder="Breve descripción del curso" />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="cap_obligatoria"
                checked={form.obligatoria}
                onChange={(e) => setForm((p) => ({ ...p, obligatoria: e.target.checked }))}
                className="h-4 w-4 cursor-pointer rounded border border-input accent-primary"
              />
              <Label htmlFor="cap_obligatoria" className="cursor-pointer font-normal">Formación obligatoria</Label>
            </div>

          </div>
          {serverError && <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>}
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>Cancelar</Button>
          <Button type="submit" form="cap-form" className="min-h-11" disabled={submitting}>
            {submitting ? "Guardando..." : isEditing ? "Guardar cambios" : "Crear formación"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
