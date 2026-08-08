"use client"

import { useCallback, useEffect, useState } from "react"
import { AlertCircle, Pencil, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { CapacitacionModal } from "@/components/features/capacitaciones/CapacitacionModal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { fetchCapacitaciones, deleteCapacitacion, exportarCatalogoCapacitaciones } from "@/services/capacitaciones"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Capacitacion } from "@/types/capacitacion"
import type { Empresa } from "@/types/empresa"

const SELECT_CLASS =
  "min-h-[2rem] rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
    </div>
  )
}

export function CatalogoTab({ canWrite }: { canWrite: boolean }) {
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [capacitaciones, setCapacitaciones] = useState<Capacitacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [soloActivos, setSoloActivos] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Capacitacion | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (!empresaActivaId) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [empresaActivaId])

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const override = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined
      const data = await fetchCapacitaciones(override, soloActivos)
      setCapacitaciones(data.items)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [empresaActivaId, empresaFiltro, soloActivos])

  useEffect(() => { load() }, [load])

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await deleteCapacitacion(id); await load() }
    catch { toast.error("No se pudo eliminar el curso. Intentá de nuevo.") }
    finally { setDeletingId(null) }
  }

  const mostrarFiltroEmpresa = !empresaActivaId && empresas.length > 0

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {mostrarFiltroEmpresa && (
            <select aria-label="Filtrar por empresa" className={SELECT_CLASS} value={empresaFiltro} onChange={(e) => setEmpresaFiltro(e.target.value)}>
              <option value="">Todas las empresas</option>
              {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
            </select>
          )}
          <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer select-none">
            <input type="checkbox" checked={soloActivos} onChange={(e) => setSoloActivos(e.target.checked)} className="h-4 w-4 rounded border border-input accent-primary" />
            Solo activos
          </label>
          {/* Los MISMOS filtros que el listado (empresa + solo activos): el archivo no puede
              traer las inactivas que la tabla está ocultando. */}
          <ExportMenu
            onExport={(f) => exportarCatalogoCapacitaciones(f, empresaActivaId ?? empresaFiltro ?? undefined, soloActivos)}
          />
        </div>
        {canWrite && (
          <Button className="min-h-11" onClick={() => { setEditing(null); setModalOpen(true) }}>
            <Plus className="size-4" />
            Nuevo curso
          </Button>
        )}
      </div>

      {loading && <TableSkeleton />}
      {!loading && error && <ErrorState action={load} />}
      {!loading && !error && capacitaciones.length === 0 && (
        <EmptyState icon={<AlertCircle />} title="Sin capacitaciones" description="No hay cursos en el catálogo para los filtros seleccionados." />
      )}

      {!loading && !error && capacitaciones.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Categoría</TableHead>
              <TableHead>Duración</TableHead>
              {!empresaActivaId && <TableHead>Empresa</TableHead>}
              <TableHead>Obligatoria</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {capacitaciones.map((c) => (
              <TableRow key={c.id}>
                <TableCell className="font-medium">{c.nombre}</TableCell>
                <TableCell className="text-muted-foreground">{c.categoria ?? "—"}</TableCell>
                <TableCell className="text-muted-foreground">{c.duracion_horas != null ? `${c.duracion_horas} hs` : "—"}</TableCell>
                {!empresaActivaId && <TableCell className="text-muted-foreground">{c.empresa_nombre ?? "—"}</TableCell>}
                <TableCell>
                  <Badge variant={c.obligatoria ? "default" : "outline"}>{c.obligatoria ? "Sí" : "No"}</Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={c.activo ? "secondary" : "outline"}>{c.activo ? "Activo" : "Inactivo"}</Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    {canWrite && (
                      <>
                        <Button variant="ghost" size="sm" onClick={() => { setEditing(c); setModalOpen(true) }} aria-label="Editar"><Pencil className="size-3.5" /></Button>
                        <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" disabled={deletingId === c.id} onClick={() => handleDelete(c.id)} aria-label="Eliminar">
                          {deletingId === c.id ? "..." : <Trash2 className="size-3.5" />}
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

      <CapacitacionModal
        open={modalOpen}
        onClose={() => { setModalOpen(false); setEditing(null) }}
        onSuccess={() => { setModalOpen(false); setEditing(null); load() }}
        editing={editing}
      />
    </div>
  )
}
