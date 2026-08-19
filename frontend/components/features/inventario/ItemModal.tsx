"use client"

import { useEffect, useState } from "react"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select } from "@/components/ui/select"
import { createItem, updateItem } from "@/services/inventario"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { InventarioItem, InventarioItemCreate, InventarioItemUpdate } from "@/types/inventario"
import type { Empresa } from "@/types/empresa"

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  editing?: InventarioItem | null
}

type FormData = { empresa_id: string; nombre: string; tipo: string; descripcion: string; numero_serie: string; costo: string; notas: string }
type FormErrors = Partial<Record<keyof FormData, string>>

const EMPTY: FormData = { empresa_id: "", nombre: "", tipo: "", descripcion: "", numero_serie: "", costo: "", notas: "" }
function validate(form: FormData, isEdit: boolean): FormErrors {
  const e: FormErrors = {}
  if (!isEdit && !form.empresa_id) e.empresa_id = "Requerido"
  if (!form.nombre.trim()) e.nombre = "Requerido"
  if (!form.tipo.trim()) e.tipo = "Requerido"
  if (form.costo && isNaN(Number(form.costo))) e.costo = "Debe ser un número"
  return e
}

export function ItemModal({ open, onClose, onSuccess, editing }: Props) {
  const isEdit = Boolean(editing)
  const [form, setForm] = useState<FormData>(EMPTY)
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")
  const [empresas, setEmpresas] = useState<Empresa[]>([])

  useEffect(() => {
    if (!open) return
    setErrors({}); setServerError("")
    if (editing) {
      setForm({
        empresa_id: editing.empresa_id, nombre: editing.nombre, tipo: editing.tipo,
        descripcion: editing.descripcion ?? "", numero_serie: editing.numero_serie ?? "",
        costo: editing.costo != null ? String(editing.costo) : "", notas: editing.notas ?? "",
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
    const errs = validate(form, isEdit)
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setSubmitting(true); setServerError("")
    try {
      if (isEdit && editing) {
        const payload: InventarioItemUpdate = {
          nombre: form.nombre.trim(), tipo: form.tipo.trim(),
          descripcion: form.descripcion.trim() || undefined,
          numero_serie: form.numero_serie.trim() || undefined,
          costo: form.costo ? Number(form.costo) : undefined,
          notas: form.notas.trim() || undefined,
        }
        await updateItem(editing.id, payload)
      } else {
        const payload: InventarioItemCreate = {
          empresa_id: form.empresa_id, nombre: form.nombre.trim(), tipo: form.tipo.trim(),
          descripcion: form.descripcion.trim() || undefined,
          numero_serie: form.numero_serie.trim() || undefined,
          costo: form.costo ? Number(form.costo) : undefined,
          notas: form.notas.trim() || undefined,
        }
        await createItem(payload)
      }
      onSuccess()
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Ocurrió un error al guardar")
    } finally { setSubmitting(false) }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>{isEdit ? "Editar ítem" : "Nuevo ítem"}</DialogTitle></DialogHeader>
        <form id="item-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">
            {!isEdit && (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="item_empresa">Empresa <span className="text-destructive" aria-hidden>*</span></Label>
                <Select id="item_empresa" value={form.empresa_id} onChange={field("empresa_id")} aria-required aria-invalid={Boolean(errors.empresa_id)}>
                  <option value="">Seleccionar empresa</option>
                  {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
                </Select>
                {errors.empresa_id && <p className="text-xs text-destructive" role="alert">{errors.empresa_id}</p>}
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="item_nombre">Nombre <span className="text-destructive" aria-hidden>*</span></Label>
                <Input id="item_nombre" value={form.nombre} onChange={field("nombre")} aria-required aria-invalid={Boolean(errors.nombre)} placeholder="ej. MacBook Pro 14" />
                {errors.nombre && <p className="text-xs text-destructive" role="alert">{errors.nombre}</p>}
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="item_tipo">Tipo <span className="text-destructive" aria-hidden>*</span></Label>
                <Input id="item_tipo" value={form.tipo} onChange={field("tipo")} aria-required aria-invalid={Boolean(errors.tipo)} placeholder="ej. Notebook" />
                {errors.tipo && <p className="text-xs text-destructive" role="alert">{errors.tipo}</p>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="item_serie">N° de serie <span className="text-xs text-muted-foreground font-normal">(opcional)</span></Label>
                <Input id="item_serie" value={form.numero_serie} onChange={field("numero_serie")} placeholder="ej. C02XK1JNJG5H" />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="item_costo">Costo <span className="text-xs text-muted-foreground font-normal">(opcional)</span></Label>
                <Input id="item_costo" type="number" min="0" step="0.01" value={form.costo} onChange={field("costo")} aria-invalid={Boolean(errors.costo)} />
                {errors.costo && <p className="text-xs text-destructive" role="alert">{errors.costo}</p>}
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item_desc">Descripción <span className="text-xs text-muted-foreground font-normal">(opcional)</span></Label>
              <Input id="item_desc" value={form.descripcion} onChange={field("descripcion")} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="item_notas">Notas <span className="text-xs text-muted-foreground font-normal">(opcional)</span></Label>
              <Textarea id="item_notas" value={form.notas} onChange={field("notas")} rows={2} className="resize-none" />
            </div>
          </div>
          {serverError && <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>}
        </form>
        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>Cancelar</Button>
          <Button type="submit" form="item-form" className="min-h-11" disabled={submitting}>
            {submitting ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear ítem"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
