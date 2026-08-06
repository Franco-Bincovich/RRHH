"use client"

import { useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { ItemModal } from "@/components/features/inventario/ItemModal"
import { ItemsInvTable } from "@/components/features/inventario/ItemsInvTable"
import { HistorialModal } from "@/components/features/inventario/HistorialModal"
import { useFiltrosItemsInv } from "@/components/features/inventario/useFiltrosItemsInv"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { deleteItem, exportarInventarioItems } from "@/services/inventario"
import type { InventarioItem } from "@/types/inventario"

const SEL = "min-h-[2rem] rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

export function ItemsTab({ canWrite }: { canWrite: boolean }) {
  const {
    empresaActivaId, empresas, empresaFiltro, cambiarEmpresa,
    estadoFiltro, setEstadoFiltro, areaFiltro, setAreaFiltro, opcionesArea,
    items, loading, error, load, filtros,
  } = useFiltrosItemsInv()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<InventarioItem | null>(null)
  const [historialItem, setHistorialItem] = useState<InventarioItem | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await deleteItem(id); await load() } catch { toast.error("No se pudo eliminar el ítem. Intentá de nuevo.") } finally { setDeletingId(null) }
  }

  const mostrarEmpresa = !empresaActivaId

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {mostrarEmpresa && empresas.length > 0 && (
            <select className={SEL} value={empresaFiltro} onChange={(e) => cambiarEmpresa(e.target.value)} aria-label="Filtrar por empresa">
              <option value="">Todas las empresas</option>
              {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
            </select>
          )}
          {opcionesArea.length > 0 && (
            <select className={SEL} value={areaFiltro} onChange={(e) => setAreaFiltro(e.target.value)} aria-label="Filtrar por área">
              <option value="">Todas las áreas</option>
              {opcionesArea.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
            </select>
          )}
          <select className={SEL} value={estadoFiltro} onChange={(e) => setEstadoFiltro(e.target.value)} aria-label="Filtrar por estado">
            <option value="">Todos los estados</option>
            <option value="disponible">Disponible</option>
            <option value="asignado">Asignado</option>
            <option value="en_reparacion">En reparación</option>
            <option value="baja">Baja</option>
          </select>
        </div>
        <div className="flex gap-2">
          <ExportMenu onExport={(f) => exportarInventarioItems(f, filtros)} />
          {canWrite && <Button className="min-h-11" onClick={() => { setEditing(null); setModalOpen(true) }}><Plus className="size-4" /> Nuevo ítem</Button>}
        </div>
      </div>

      <ItemsInvTable
        items={items} loading={loading} error={error} canWrite={canWrite}
        mostrarEmpresa={mostrarEmpresa} deletingId={deletingId} onReload={load}
        onHistorial={setHistorialItem}
        onEditar={(item) => { setEditing(item); setModalOpen(true) }}
        onEliminar={handleDelete}
      />

      <ItemModal open={modalOpen} onClose={() => { setModalOpen(false); setEditing(null) }} onSuccess={() => { setModalOpen(false); setEditing(null); load() }} editing={editing} />
      {historialItem && <HistorialModal item={historialItem} onClose={() => setHistorialItem(null)} />}
    </div>
  )
}
