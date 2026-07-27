"use client"

import { useCallback, useEffect, useState } from "react"
import { AlertCircle, History, Pencil, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ItemModal } from "@/components/features/inventario/ItemModal"
import { HistorialModal } from "@/components/features/inventario/HistorialModal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { fetchItems, deleteItem, exportarInventarioItems } from "@/services/inventario"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { InventarioItem } from "@/types/inventario"
import type { Empresa } from "@/types/empresa"

const SEL = "min-h-[2rem] rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

const ESTADO_BADGE: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  disponible: "default", asignado: "secondary", en_reparacion: "outline", baja: "destructive",
}
const ESTADO_LABEL: Record<string, string> = {
  disponible: "Disponible", asignado: "Asignado", en_reparacion: "En reparación", baja: "Baja",
}

function Skeleton5() {
  return <div className="space-y-2">{Array.from({length:5}).map((_,i)=><Skeleton key={i} className="h-12 w-full rounded-lg"/>)}</div>
}

function formatDate(s: string) {
  const [y,m,d] = s.split("-"); return `${d}/${m}/${y}`
}

export function ItemsTab({ canWrite }: { canWrite: boolean }) {
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [items, setItems] = useState<InventarioItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [estadoFiltro, setEstadoFiltro] = useState("")
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<InventarioItem | null>(null)
  const [historialItem, setHistorialItem] = useState<InventarioItem | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (!empresaActivaId)
      fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [empresaActivaId])

  const load = useCallback(async () => {
    setLoading(true); setError(false)
    try {
      const override = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined
      const data = await fetchItems({ empresaIdOverride: override, estado: estadoFiltro || undefined })
      setItems(data.items)
    } catch { setError(true) }
    finally { setLoading(false) }
  }, [empresaActivaId, empresaFiltro, estadoFiltro])

  useEffect(() => { load() }, [load])

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
            <select className={SEL} value={empresaFiltro} onChange={(e) => setEmpresaFiltro(e.target.value)} aria-label="Filtrar por empresa">
              <option value="">Todas las empresas</option>
              {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
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
          <ExportMenu onExport={(f) => exportarInventarioItems(f, { empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined, estado: estadoFiltro || undefined })} />
          {canWrite && <Button className="min-h-11" onClick={() => { setEditing(null); setModalOpen(true) }}><Plus className="size-4" /> Nuevo ítem</Button>}
        </div>
      </div>

      {loading && <Skeleton5 />}
      {!loading && error && <ErrorState action={load} />}
      {!loading && !error && items.length === 0 && (
        <EmptyState icon={<AlertCircle />} title="Sin ítems" description="No hay ítems de inventario para los filtros seleccionados." />
      )}
      {!loading && !error && items.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>N° Serie</TableHead>
              <TableHead>Estado</TableHead>
              {mostrarEmpresa && <TableHead>Empresa</TableHead>}
              <TableHead>Asignado a</TableHead>
              <TableHead>Alta</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-medium">{item.nombre}</TableCell>
                <TableCell className="text-muted-foreground">{item.tipo}</TableCell>
                <TableCell className="text-muted-foreground">{item.numero_serie ?? "—"}</TableCell>
                <TableCell>
                  <Badge variant={ESTADO_BADGE[item.estado] ?? "outline"}>{ESTADO_LABEL[item.estado] ?? item.estado}</Badge>
                </TableCell>
                {mostrarEmpresa && <TableCell className="text-muted-foreground">{item.empresa_nombre ?? "—"}</TableCell>}
                <TableCell className="text-muted-foreground">{item.asignado_a ?? "—"}</TableCell>
                <TableCell className="text-muted-foreground">{formatDate(item.fecha_alta)}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => setHistorialItem(item)} aria-label="Historial"><History className="size-3.5" /></Button>
                    {canWrite && (
                      <>
                        <Button variant="ghost" size="sm" onClick={() => { setEditing(item); setModalOpen(true) }} aria-label="Editar"><Pencil className="size-3.5" /></Button>
                        <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" disabled={deletingId === item.id} onClick={() => handleDelete(item.id)} aria-label="Eliminar">
                          {deletingId === item.id ? "..." : <Trash2 className="size-3.5" />}
                        </Button>
                      </>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      <ItemModal open={modalOpen} onClose={() => { setModalOpen(false); setEditing(null) }} onSuccess={() => { setModalOpen(false); setEditing(null); load() }} editing={editing} />
      {historialItem && <HistorialModal item={historialItem} onClose={() => setHistorialItem(null)} />}
    </div>
  )
}
