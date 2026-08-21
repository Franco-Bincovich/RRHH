"use client"

import { useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { ItemModal } from "@/components/features/inventario/ItemModal"
import { ItemsInvTable } from "@/components/features/inventario/ItemsInvTable"
import { HistorialModal } from "@/components/features/inventario/HistorialModal"
import { useFiltrosItemsInv } from "@/components/features/inventario/useFiltrosItemsInv"
import { useListadoItemsInv } from "@/components/features/inventario/useListadoItemsInv"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { deleteItem, exportarInventarioItems } from "@/services/inventario"
import type { InventarioItem } from "@/types/inventario"

// El tab es dueño de la página Y de su tamaño, y le pasa los dos al hook: así el número con el
// que se PIDE la página es el mismo con el que se DIBUJA la barra. Dos constantes en archivos
// distintos se despegan sin que nada falle — la barra diría "de 7 páginas" sobre 5 reales.
const PAGE_SIZE = 20

export function ItemsTab({ canWrite }: { canWrite: boolean }) {
  const [page, setPage] = useState(1)
  // 🔴 TODO cambio de filtro vuelve a la página 1 (invariante 4 del bloque B). Sin esto, filtrar
  // parado en la página 7 pide una página que el resultado nuevo no tiene y la tabla sale vacía
  // sobre un filtro que sí tiene filas — se lee como "no hay nada", no como "estás en la 7".
  const { empresaActivaId, campos, filtros } = useFiltrosItemsInv(() => setPage(1))
  const { items, loading, error, total, load } = useListadoItemsInv(filtros, page, PAGE_SIZE)
  const chips = chipsDeCampos(campos)

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<InventarioItem | null>(null)
  const [historialItem, setHistorialItem] = useState<InventarioItem | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await deleteItem(id); await load() } catch { toast.error("No se pudo eliminar el ítem. Intentá de nuevo.") } finally { setDeletingId(null) }
  }

  const mostrarEmpresa = !empresaActivaId
  const nuevoBtn = (
    <Button className="min-h-11" onClick={() => { setEditing(null); setModalOpen(true) }}>
      <Plus className="size-4" /> Nuevo ítem
    </Button>
  )

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        {/* `panel`: la forma completa del patrón de filtros. Reemplaza a los tres `<Select>`
            sueltos que esta pestaña dibujaba a mano, y que quedaban activos SIN chip. */}
        <div className="min-w-[18rem] flex-1"><FiltersBar campos={campos} panel disabled={loading} /></div>
        <div className="flex gap-2">
          <ExportMenu onExport={(f) => exportarInventarioItems(f, filtros)} />
          {canWrite && nuevoBtn}
        </div>
      </div>

      <ItemsInvTable
        items={items} loading={loading} error={error} canWrite={canWrite}
        mostrarEmpresa={mostrarEmpresa} deletingId={deletingId} onReload={load}
        onHistorial={setHistorialItem}
        onEditar={(item) => { setEditing(item); setModalOpen(true) }}
        onEliminar={handleDelete}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? nuevoBtn : undefined}
      />

      {/* 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS (era `total > PAGE_SIZE`) y sólo después de cargar:
          sin la guarda, la barra queda mostrando el total del pedido ANTERIOR sobre el esqueleto.
          El total es el del backend, no `items.length`. */}
      {!loading && !error && items.length > 0 && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}

      <ItemModal open={modalOpen} onClose={() => { setModalOpen(false); setEditing(null) }} onSuccess={() => { setModalOpen(false); setEditing(null); load() }} editing={editing} />
      {historialItem && <HistorialModal item={historialItem} onClose={() => setHistorialItem(null)} />}
    </div>
  )
}
