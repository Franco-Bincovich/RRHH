"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Select } from "@/components/ui/select"
import { fetchEmpresas } from "@/services/empresas"
import type { Empresa } from "@/types/empresa"
import type { Proyecto, ProyectoCreate, ProyectoEstado, ProyectoUpdate } from "@/types/proyecto"

type SavePayload = ProyectoCreate | ProyectoUpdate

interface Props {
  open: boolean
  proyecto: Proyecto | null   // null = crear
  onClose: () => void
  onSave: (body: SavePayload) => Promise<void>
}

const ESTADOS = ["activo", "pausado", "cerrado", "cancelado"] as const
const INPUT_CLS = "flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
const LABEL_CLS = "block text-xs font-medium text-foreground mb-1"

export function ProyectoModal({ open, proyecto, onClose, onSave }: Props) {
  const isEdit = proyecto !== null
  const [empresas, setEmpresas]     = useState<Empresa[]>([])
  const [empresa_id, setEmpresaId]  = useState("")
  const [nombre, setNombre]         = useState("")
  const [descripcion, setDescripcion] = useState("")
  const [estado, setEstado]         = useState<ProyectoEstado>("activo")
  const [fechaInicio, setFechaInicio] = useState("")
  const [fechaFin, setFechaFin]     = useState("")
  const [presupuesto, setPresupuesto] = useState("0")
  const [saving, setSaving]         = useState(false)

  useEffect(() => {
    if (!open) return
    fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
    if (proyecto) {
      setNombre(proyecto.nombre)
      setDescripcion(proyecto.descripcion ?? "")
      setEstado(proyecto.estado)
      setFechaInicio(proyecto.fecha_inicio ?? "")
      setFechaFin(proyecto.fecha_fin ?? "")
      setPresupuesto(String(proyecto.presupuesto))
    } else {
      setNombre(""); setDescripcion(""); setEstado("activo")
      setFechaInicio(""); setFechaFin(""); setPresupuesto("0"); setEmpresaId("")
    }
  }, [open, proyecto])

  async function handleSubmit() {
    if (!nombre.trim()) return
    setSaving(true)
    try {
      const base = {
        nombre: nombre.trim(), descripcion: descripcion || undefined,
        estado, presupuesto: parseFloat(presupuesto) || 0,
        fecha_inicio: fechaInicio || undefined, fecha_fin: fechaFin || undefined,
      }
      await onSave(isEdit ? base : { ...base, empresa_id })
    } catch {
      toast.error("No se pudo guardar el proyecto. Intentá de nuevo.")
    } finally { setSaving(false) }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-base">{isEdit ? "Editar proyecto" : "Nuevo proyecto"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          {!isEdit && (
            <div>
              <label className={LABEL_CLS}>Empresa dueña</label>
              <Select value={empresa_id} onChange={(e) => setEmpresaId(e.target.value)}>
                <option value="">Seleccioná una empresa</option>
                {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
              </Select>
            </div>
          )}
          <div>
            <label className={LABEL_CLS}>Nombre *</label>
            <input className={INPUT_CLS} value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nombre del proyecto" />
          </div>
          <div>
            <label className={LABEL_CLS}>Descripción</label>
            <textarea className={INPUT_CLS} rows={2} value={descripcion} onChange={(e) => setDescripcion(e.target.value)} placeholder="Descripción (opcional)" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={LABEL_CLS}>Estado</label>
              <Select value={estado} onChange={(e) => setEstado(e.target.value as ProyectoEstado)}>
                {ESTADOS.map((s) => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
              </Select>
            </div>
            <div>
              <label className={LABEL_CLS}>Presupuesto (ARS)</label>
              <input type="number" min="0" step="1000" className={INPUT_CLS} value={presupuesto}
                onChange={(e) => setPresupuesto(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={LABEL_CLS}>Inicio</label>
              <input type="date" className={INPUT_CLS} value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} />
            </div>
            <div>
              <label className={LABEL_CLS}>Fin estimado</label>
              <input type="date" className={INPUT_CLS} value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" className="min-h-[2.75rem]" onClick={onClose}>Cancelar</Button>
            <Button size="sm" className="min-h-[2.75rem]" onClick={handleSubmit}
              disabled={saving || !nombre.trim() || (!isEdit && !empresa_id)}>
              {saving ? "Guardando…" : isEdit ? "Guardar" : "Crear proyecto"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
