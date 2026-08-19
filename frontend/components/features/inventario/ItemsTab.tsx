"use client"

import { useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { ItemModal } from "@/components/features/inventario/ItemModal"
import { ItemsInvTable } from "@/components/features/inventario/ItemsInvTable"
import { HistorialModal } from "@/components/features/inventario/HistorialModal"
import { useFiltrosItemsInv } from "@/components/features/inventario/useFiltrosItemsInv"
import { Pagination } from "@/components/ui/Pagination"
import { Select } from "@/components/ui/select"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { deleteItem, exportarInventarioItems } from "@/services/inventario"
import type { InventarioItem } from "@/types/inventario"

// El tab es dueño de la página Y de su tamaño, y le pasa los dos al hook: así el número con el
// que se PIDE la página es el mismo con el que se DIBUJA la barra. Dos constantes en archivos
// distintos se despegan sin que nada falle — la barra diría "de 7 páginas" sobre 5 reales.
const PAGE_SIZE = 20

export function ItemsTab({ canWrite }: { canWrite: boolean }) {
  const [page, setPage] = useState(1)
  const {
    empresaActivaId, empresas, empresaFiltro, cambiarEmpresa,
    estadoFiltro, setEstadoFiltro, areaFiltro, setAreaFiltro, opcionesArea,
    items, loading, error, load, filtros, total,
  } = useFiltrosItemsInv(page, PAGE_SIZE)
  // 🔴 TODO cambio de filtro vuelve a la página 1 (invariante 4 del bloque B). Sin esto, filtrar
  // parado en la página 7 pide una página que el resultado nuevo no tiene y la tabla sale vacía
  // sobre un filtro que sí tiene filas — se lee como "no hay nada", no como "estás en la 7".
  const filtrar = <T,>(fn: (v: T) => void) => (v: T) => { setPage(1); fn(v) }
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
            <Select size="sm" className="w-auto" value={empresaFiltro} onChange={(e) => filtrar(cambiarEmpresa)(e.target.value)} aria-label="Filtrar por empresa">
              <option value="">Todas las empresas</option>
              {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
            </Select>
          )}
          {opcionesArea.length > 0 && (
            <Select size="sm" className="w-auto" value={areaFiltro} onChange={(e) => filtrar(setAreaFiltro)(e.target.value)} aria-label="Filtrar por área">
              <option value="">Todas las áreas</option>
              {opcionesArea.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
            </Select>
          )}
          <Select size="sm" className="w-auto" value={estadoFiltro} onChange={(e) => filtrar(setEstadoFiltro)(e.target.value)} aria-label="Filtrar por estado">
            <option value="">Todos los estados</option>
            <option value="disponible">Disponible</option>
            <option value="asignado">Asignado</option>
            <option value="en_reparacion">En reparación</option>
            <option value="baja">Baja</option>
          </Select>
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

      {total > PAGE_SIZE && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}

      <ItemModal open={modalOpen} onClose={() => { setModalOpen(false); setEditing(null) }} onSuccess={() => { setModalOpen(false); setEditing(null); load() }} editing={editing} />
      {historialItem && <HistorialModal item={historialItem} onClose={() => setHistorialItem(null)} />}
    </div>
  )
}
