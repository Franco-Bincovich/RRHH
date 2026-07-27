"use client"

import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { asignarBulk } from "@/services/proyectos"
import { fetchAreas } from "@/services/areas"
import { fetchEmpleados } from "@/services/empleados"
import type { Empleado } from "@/types/empleado"
import type { Area } from "@/types/area"

interface Props {
  open: boolean
  proyectoId: string
  onClose: () => void
  onSuccess: () => void
}

const INPUT_CLS = "flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
const LABEL_CLS = "block text-xs font-medium text-foreground mb-1"

/** Alta multi-selección. El área FILTRA la lista de candidatos (no asigna el área completa). */
export function AsignarEmpleadosModal({ open, proyectoId, onClose, onSuccess }: Props) {
  const [empleados, setEmpleados] = useState<Empleado[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [areaFiltro, setAreaFiltro] = useState("")
  const [search, setSearch] = useState("")
  const [sel, setSel] = useState<Set<string>>(new Set())
  const [rol, setRol] = useState("")
  const [valorHora, setValorHora] = useState("0")
  const [fechaDesde, setFechaDesde] = useState("")
  const [fechaHasta, setFechaHasta] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setSel(new Set()); setSearch(""); setAreaFiltro(""); setRol(""); setValorHora("0"); setFechaDesde(""); setFechaHasta("")
    fetchAreas(undefined).then(setAreas).catch(() => setAreas([]))
  }, [open])

  // Candidatos: activos de TODAS las empresas del grupo, acotados por área server-side (param areaId).
  useEffect(() => {
    if (!open) return
    fetchEmpleados({ page: 1, pageSize: 200, estado: "activo", empresaId: "todas", areaId: areaFiltro || undefined })
      .then((r) => setEmpleados(r.items ?? [])).catch(() => setEmpleados([]))
  }, [open, areaFiltro])

  const visibles = useMemo(() => {
    const q = search.trim().toLowerCase()
    return q ? empleados.filter((e) => `${e.nombre} ${e.apellido}`.toLowerCase().includes(q)) : empleados
  }, [empleados, search])

  const allSelected = visibles.length > 0 && visibles.every((e) => sel.has(e.id))

  function toggle(id: string) {
    setSel((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })
  }
  function toggleAll() {
    setSel((prev) => { const n = new Set(prev); visibles.forEach((e) => allSelected ? n.delete(e.id) : n.add(e.id)); return n })
  }

  async function handleSubmit() {
    if (sel.size === 0 || !rol.trim()) return
    setSaving(true)
    try {
      const res = await asignarBulk(proyectoId, {
        empleado_ids: [...sel], rol: rol.trim(), valor_hora: parseFloat(valorHora) || 0,
        fecha_desde: fechaDesde || undefined, fecha_hasta: fechaHasta || undefined,
      })
      const ok = `${res.asignados.length} empleado${res.asignados.length !== 1 ? "s" : ""} asignado${res.asignados.length !== 1 ? "s" : ""}`
      if (res.errores.length) toast.warning(`${ok}. ${res.errores.length} no se pudieron (ya asignados o inactivos).`)
      else toast.success(ok)
      onSuccess()
    } catch { toast.error("No se pudo asignar. Intentá de nuevo.") }
    finally { setSaving(false) }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle className="text-base">Asignar empleados</DialogTitle></DialogHeader>
        <div className="space-y-4 pt-2">
          <div className="grid grid-cols-2 gap-3">
            <select className={INPUT_CLS} value={areaFiltro} onChange={(e) => setAreaFiltro(e.target.value)} aria-label="Filtrar por área">
              <option value="">Todas las áreas</option>
              {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
            </select>
            <input className={INPUT_CLS} type="search" value={search} placeholder="Buscar por nombre…" onChange={(e) => setSearch(e.target.value)} />
          </div>

          <div className="rounded-md border">
            <label className="flex items-center gap-2 border-b px-3 py-2 text-xs font-medium text-muted-foreground">
              <input type="checkbox" checked={allSelected} onChange={toggleAll} />
              Seleccionar todos ({sel.size} seleccionado{sel.size !== 1 ? "s" : ""})
            </label>
            <div className="max-h-52 divide-y overflow-y-auto">
              {visibles.length === 0 ? (
                <p className="px-3 py-6 text-center text-sm text-muted-foreground">Sin candidatos.</p>
              ) : visibles.map((e) => (
                <label key={e.id} className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm">
                  <input type="checkbox" checked={sel.has(e.id)} onChange={() => toggle(e.id)} />
                  <span className="flex-1 text-foreground">{e.nombre} {e.apellido}</span>
                  {e.empresa_nombre && <Badge variant="secondary" className="text-xs">{e.empresa_nombre}</Badge>}
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 sm:col-span-1">
              <label className={LABEL_CLS}>Rol en el proyecto</label>
              <input className={INPUT_CLS} value={rol} onChange={(e) => setRol(e.target.value)} placeholder="Ej: Desarrollador" />
            </div>
            <div className="col-span-2 sm:col-span-1">
              <label className={LABEL_CLS}>Valor/hora (ARS)</label>
              <input type="number" min="0" step="100" className={INPUT_CLS} value={valorHora} onChange={(e) => setValorHora(e.target.value)} />
            </div>
            <div><label className={LABEL_CLS}>Desde</label><input type="date" className={INPUT_CLS} value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} /></div>
            <div><label className={LABEL_CLS}>Hasta</label><input type="date" className={INPUT_CLS} value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} /></div>
          </div>

          <p className="text-xs text-muted-foreground">Todos comparten rol, valor/hora y fechas. Editá cada uno después si difieren.</p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" className="min-h-[2.75rem]" onClick={onClose}>Cancelar</Button>
            <Button size="sm" className="min-h-[2.75rem]" onClick={handleSubmit} disabled={saving || sel.size === 0 || !rol.trim()}>
              {saving ? "Asignando…" : `Asignar (${sel.size})`}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
