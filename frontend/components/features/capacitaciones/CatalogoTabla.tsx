"use client"

import { AlertCircle, Pencil, Trash2 } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Capacitacion } from "@/types/capacitacion"

/**
 * Los cuatro estados de render del catálogo de cursos: cargando, error, vacío y la tabla.
 *
 * Extraído de `CatalogoTab.tsx` (159/150) para poder sumarle el import por Excel. El corte deja
 * el módulo SIMÉTRICO con su hermano, que ya tenía este reparto: `AsignacionesTab` (96,
 * orquestador) + `AsignacionesCapTable` (134, presentacional). El catálogo era el único de los
 * dos tabs que hacía las dos cosas en un archivo.
 *
 * Presentacional puro: sin estado, sin fetch. Los cuatro estados viven juntos y no en el
 * orquestador a propósito — son excluyentes entre sí y decidirlos en dos archivos distintos es
 * cómo aparece la pantalla que muestra el vacío mientras carga.
 */
interface Props {
  capacitaciones: Capacitacion[]
  loading: boolean
  error: boolean
  onReintentar: () => void
  canWrite: boolean
  /** `null` = ninguna borrándose. Deshabilita solo la fila en curso. */
  deletingId: string | null
  onEditar: (c: Capacitacion) => void
  onEliminar: (id: string) => void
  /** El modo consolidado agrega la columna de empresa: un mismo curso puede existir en varias. */
  mostrarEmpresa: boolean
}

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
    </div>
  )
}

export function CatalogoTabla({
  capacitaciones, loading, error, onReintentar, canWrite, deletingId,
  onEditar, onEliminar, mostrarEmpresa,
}: Props) {
  if (loading) return <TableSkeleton />
  if (error) return <ErrorState action={onReintentar} />
  if (capacitaciones.length === 0) {
    return (
      <EmptyState
        icon={<AlertCircle />}
        title="Sin formaciones"
        description="No hay cursos en el catálogo para los filtros seleccionados."
      />
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Nombre</TableHead>
          <TableHead>Categoría</TableHead>
          <TableHead>Duración</TableHead>
          {mostrarEmpresa && <TableHead>Empresa</TableHead>}
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
            {mostrarEmpresa && <TableCell className="text-muted-foreground">{c.empresa_nombre ?? "—"}</TableCell>}
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
                    <Button variant="ghost" size="sm" onClick={() => onEditar(c)} aria-label="Editar"><Pencil className="size-3.5" /></Button>
                    <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" disabled={deletingId === c.id} onClick={() => onEliminar(c.id)} aria-label="Eliminar">
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
  )
}
