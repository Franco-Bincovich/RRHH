"use client"

import { useState, useEffect } from "react"
import { Plus, Pencil, Trash2, Layers } from "lucide-react"
import { toast } from "sonner"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
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
import { fetchAreas, deleteArea } from "@/services/areas"
import type { Area } from "@/types/area"

interface EmpresaAreasTabProps {
  empresaId: string
  canWrite: boolean
}

export function EmpresaAreasTab({ empresaId, canWrite }: EmpresaAreasTabProps) {
  const [areas, setAreas] = useState<Area[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Area | undefined>(undefined)
  const [confirmDelete, setConfirmDelete] = useState<Area | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function load() {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchAreas(empresaId)
      setAreas(data)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [empresaId])

  function openCreate() {
    setEditing(undefined)
    setModalOpen(true)
  }

  function openEdit(area: Area) {
    setEditing(area)
    setModalOpen(true)
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
      <div className="space-y-2 pt-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full rounded-lg" />
        ))}
      </div>
    )
  }

  if (error) {
    return <ErrorState description="No se pudieron cargar las áreas." action={load} />
  }

  return (
    <div>
      <div className="mb-4 flex justify-end">
        {canWrite && (
          <Button className="min-h-11" onClick={openCreate}>
            <Plus />
            Nueva área
          </Button>
        )}
      </div>

      {areas.length === 0 ? (
        <EmptyState
          icon={<Layers />}
          title="Sin áreas"
          description="Esta empresa no tiene áreas todavía. Creá la primera."
          action={
            canWrite ? (
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
              <TableHead className="text-right">Colaboradores</TableHead>
              <TableHead className="w-24 text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {areas.map((area) => (
              <TableRow key={area.id}>
                <TableCell className="font-medium">{area.nombre}</TableCell>
                <TableCell className="text-muted-foreground">
                  {area.descripcion ?? <span className="italic text-muted-foreground/60">—</span>}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {area.responsable_nombre ?? <span className="italic text-muted-foreground/60">—</span>}
                </TableCell>
                <TableCell className="text-right tabular-nums">{area.cantidad_empleados}</TableCell>
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
        onSuccess={() => { setModalOpen(false); void load() }}
        area={editing}
        empresaId={empresaId}
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
            <Button variant="outline" className="min-h-11" onClick={() => setConfirmDelete(null)} disabled={deleting}>
              Cancelar
            </Button>
            <Button variant="destructive" className="min-h-11" onClick={handleDelete} disabled={deleting}>
              {deleting ? "Eliminando..." : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
