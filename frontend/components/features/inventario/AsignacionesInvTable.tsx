"use client"

/**
 * Tabla de asignaciones de inventario: presentacional. Cubre los cuatro estados del listado
 * (cargando / error / vacío / datos) y no sabe nada de filtros ni de fetch — extraída de
 * AsignacionesTab, que estaba clavado en 150/150.
 *
 * Muestra solo asignaciones VIGENTES: el repo filtra fecha_devolucion IS NULL
 * (inventario_asignaciones_repo.find_all), por eso el estado vacío habla de "activas".
 */
import { AlertCircle } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Asignacion } from "@/types/inventario"

function Skeleton5() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
    </div>
  )
}

function formatDate(s: string | null): string {
  if (!s) return "—"
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y}`
}

interface AsignacionesInvTableProps {
  asignaciones: Asignacion[]
  loading: boolean
  error: boolean
  canWrite: boolean
  mostrarEmpresa: boolean
  onReload: () => void
  onDevolver: (a: Asignacion) => void
}

export function AsignacionesInvTable({
  asignaciones, loading, error, canWrite, mostrarEmpresa, onReload, onDevolver,
}: AsignacionesInvTableProps) {
  if (loading) return <Skeleton5 />
  if (error) return <ErrorState action={onReload} />
  if (asignaciones.length === 0) {
    return (
      <EmptyState
        icon={<AlertCircle />} title="Sin asignaciones activas"
        description="No hay ítems asignados actualmente."
      />
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Colaborador</TableHead>
          <TableHead>Ítem</TableHead>
          <TableHead>Tipo</TableHead>
          <TableHead>N° Serie</TableHead>
          {mostrarEmpresa && <TableHead>Empresa</TableHead>}
          <TableHead>Desde</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {asignaciones.map((a) => (
          <TableRow key={a.id}>
            <TableCell className="font-medium">{a.empleado_nombre ?? "—"}</TableCell>
            <TableCell>{a.item_nombre ?? "—"}</TableCell>
            <TableCell className="text-muted-foreground">{a.item_tipo ?? "—"}</TableCell>
            <TableCell className="text-muted-foreground">{a.item_numero_serie ?? "—"}</TableCell>
            {mostrarEmpresa && <TableCell className="text-muted-foreground">{a.empresa_nombre ?? "—"}</TableCell>}
            <TableCell className="text-muted-foreground">{formatDate(a.fecha_asignacion)}</TableCell>
            <TableCell>
              {canWrite && (
                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => onDevolver(a)}>
                  Devolver
                </Button>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
