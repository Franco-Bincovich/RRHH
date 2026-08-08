"use client"

import { useState, useEffect, useMemo } from "react"
import { Plus, Search, Layers, Pencil, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { AreaModal } from "@/components/features/areas/AreaModal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { fetchAreas, deleteArea, exportarAreas } from "@/services/areas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Area } from "@/types/area"

export default function AreasPage() {
  const canWrite = useCanWrite()
  const [areas, setAreas] = useState<Area[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [search, setSearch] = useState("")
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Area | undefined>(undefined)
  const [confirmDelete, setConfirmDelete] = useState<Area | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function load() {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchAreas(getEmpresaActivaId() ?? undefined)
      setAreas(data)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const filtered = useMemo(() => {
    if (!search.trim()) return areas
    const q = search.trim().toLowerCase()
    return areas.filter((a) => a.nombre.toLowerCase().includes(q))
  }, [areas, search])

  function openCreate() {
    setEditing(undefined)
    setModalOpen(true)
  }

  function openEdit(area: Area) {
    setEditing(area)
    setModalOpen(true)
  }

  function handleModalSuccess() {
    setModalOpen(false)
    void load()
  }

  async function handleDelete() {
    if (!confirmDelete) return
    setDeleting(true)
    try {
      await deleteArea(confirmDelete.id)
      setConfirmDelete(null)
      void load()
    } catch {
      toast.error("No se pudo eliminar el área. Intentá de nuevo.")
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div>
        <PageHeader title="Áreas" description="Cargando..." />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Áreas" />
        <ErrorState
          description="No se pudieron cargar las áreas."
          action={load}
        />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Áreas"
        description={`${areas.length} área${areas.length !== 1 ? "s" : ""}`}
        action={
          <div className="flex items-center gap-2">
            {/* El MISMO filtro de empresa que el listado. ⚠️ El buscador de abajo es
                CLIENT-SIDE, así que el archivo trae todas las áreas de la empresa, no las que
                el buscador deja a la vista. Con 12 áreas es tolerable; el día que crezca, ese
                `search` tiene que pasar al backend (regla del bloque B). */}
            <ExportMenu
              onExport={(formato) => exportarAreas(formato, getEmpresaActivaId() ?? undefined)}
            />
            {canWrite && (
              <Button className="min-h-11" onClick={openCreate}>
                <Plus />
                Nueva área
              </Button>
            )}
          </div>
        }
      />

      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Layers />}
          title={search ? "Sin resultados" : "Sin áreas"}
          description={
            search
              ? "No hay áreas que coincidan con la búsqueda."
              : "Todavía no hay áreas registradas. Creá la primera."
          }
          action={
            !search && canWrite ? (
              <Button className="min-h-11" onClick={openCreate}>
                <Plus />
                Nueva área
              </Button>
            ) : undefined
          }
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Descripción</TableHead>
              <TableHead>Responsable</TableHead>
              <TableHead className="text-right">Empleados</TableHead>
              <TableHead className="w-24 text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((area) => (
              <TableRow key={area.id}>
                <TableCell className="font-medium">{area.nombre}</TableCell>
                <TableCell className="text-muted-foreground">
                  {area.descripcion ?? <span className="italic text-muted-foreground/60">—</span>}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {area.responsable_nombre ?? <span className="italic text-muted-foreground/60">—</span>}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {area.cantidad_empleados}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    {canWrite && (
                      <>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-9"
                          aria-label={`Editar ${area.nombre}`}
                          onClick={() => openEdit(area)}
                        >
                          <Pencil className="size-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-9 text-destructive hover:text-destructive"
                          aria-label={`Eliminar ${area.nombre}`}
                          onClick={() => setConfirmDelete(area)}
                        >
                          <Trash2 className="size-4" />
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

      <AreaModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={handleModalSuccess}
        area={editing}
        empresaId={getEmpresaActivaId() ?? undefined}
      />

      <Dialog open={Boolean(confirmDelete)} onOpenChange={(o) => { if (!o) setConfirmDelete(null) }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Eliminar área</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            ¿Estás seguro de que querés eliminar{" "}
            <span className="font-medium text-foreground">{confirmDelete?.nombre}</span>?
            Esta acción no se puede deshacer.
          </p>
          <DialogFooter>
            <Button
              variant="outline"
              className="min-h-11"
              onClick={() => setConfirmDelete(null)}
              disabled={deleting}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              className="min-h-11"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? "Eliminando..." : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
