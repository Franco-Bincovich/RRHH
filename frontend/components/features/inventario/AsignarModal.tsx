"use client"

import { useEffect, useState } from "react"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { EmpleadoCombobox } from "@/components/features/shared/EmpleadoCombobox"
import { asignarItem, fetchItems } from "@/services/inventario"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { AsignacionCreate, InventarioItem } from "@/types/inventario"
import type { Empresa } from "@/types/empresa"

interface Props { open: boolean; onClose: () => void; onSuccess: () => void }

type FormData = { empresa_id: string; item_id: string; empleado_id: string }
type FormErrors = Partial<Record<keyof FormData, string>>

const EMPTY: FormData = { empresa_id: "", item_id: "", empleado_id: "" }
function validate(form: FormData): FormErrors {
  const e: FormErrors = {}
  if (!form.empresa_id) e.empresa_id = "Requerido"
  if (!form.item_id)    e.item_id    = "Requerido"
  if (!form.empleado_id) e.empleado_id = "Requerido"
  return e
}

export function AsignarModal({ open, onClose, onSuccess }: Props) {
  const [form, setForm] = useState<FormData>(EMPTY)
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [items, setItems] = useState<InventarioItem[]>([])
  const [loadingItems, setLoadingItems] = useState(false)

  useEffect(() => {
    if (!open) return
    setErrors({}); setServerError("")
    setForm({ ...EMPTY, empresa_id: getEmpresaActivaId() ?? "" })
  }, [open])

  useEffect(() => {
    if (!open) return
    fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [open])

  useEffect(() => {
    if (!form.empresa_id) { setItems([]); return }
    setLoadingItems(true)
    fetchItems({ empresaIdOverride: form.empresa_id, estado: "disponible" })
      .then((r) => setItems(r.items)).catch(() => setItems([])).finally(() => setLoadingItems(false))
    // Los empleados ya no se precargan acá: los busca `EmpleadoCombobox` contra el backend.
  }, [form.empresa_id])

  function field(key: keyof FormData) {
    return (e: React.ChangeEvent<HTMLSelectElement>) => {
      setForm((p) => ({ ...p, [key]: e.target.value }))
      if (errors[key]) setErrors((p) => ({ ...p, [key]: undefined }))
    }
  }

  function handleEmpresaChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setForm((p) => ({ ...p, empresa_id: e.target.value, item_id: "", empleado_id: "" }))
    setErrors((p) => ({ ...p, empresa_id: undefined, item_id: undefined, empleado_id: undefined }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate(form)
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setSubmitting(true); setServerError("")
    try {
      const payload: AsignacionCreate = { item_id: form.item_id, empleado_id: form.empleado_id }
      await asignarItem(payload)
      onSuccess()
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Ocurrió un error al asignar")
    } finally { setSubmitting(false) }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>Asignar ítem</DialogTitle></DialogHeader>
        <form id="asig-inv-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="asig_empresa">Empresa <span className="text-destructive" aria-hidden>*</span></Label>
              <Select id="asig_empresa" value={form.empresa_id} onChange={handleEmpresaChange} aria-required aria-invalid={Boolean(errors.empresa_id)}>
                <option value="">Seleccionar empresa</option>
                {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
              </Select>
              {errors.empresa_id && <p className="text-xs text-destructive" role="alert">{errors.empresa_id}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="asig_item">Ítem disponible <span className="text-destructive" aria-hidden>*</span></Label>
              <Select id="asig_item" value={form.item_id} onChange={field("item_id")} disabled={!form.empresa_id || loadingItems} aria-required aria-invalid={Boolean(errors.item_id)}>
                <option value="">{!form.empresa_id ? "Seleccioná una empresa primero" : loadingItems ? "Cargando..." : items.length === 0 ? "Sin ítems disponibles" : "Seleccionar ítem"}</option>
                {items.map((i) => <option key={i.id} value={i.id}>{i.nombre}{i.numero_serie ? ` — ${i.numero_serie}` : ""}</option>)}
              </Select>
              {errors.item_id && <p className="text-xs text-destructive" role="alert">{errors.item_id}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="asig_emp">Colaborador <span className="text-destructive" aria-hidden>*</span></Label>
              <EmpleadoCombobox
                id="asig_emp" value={form.empleado_id} empresaId={form.empresa_id || undefined}
                disabled={!form.empresa_id} mensajeDeshabilitado="Seleccioná una empresa primero"
                invalid={Boolean(errors.empleado_id)}
                onChange={(emp) => {
                  setForm((p) => ({ ...p, empleado_id: emp?.id ?? "" }))
                  setErrors((p) => ({ ...p, empleado_id: undefined }))
                }}
              />
              {errors.empleado_id && <p className="text-xs text-destructive" role="alert">{errors.empleado_id}</p>}
            </div>
          </div>
          {serverError && <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>}
        </form>
        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>Cancelar</Button>
          <Button type="submit" form="asig-inv-form" className="min-h-11" disabled={submitting}>{submitting ? "Asignando..." : "Asignar"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
