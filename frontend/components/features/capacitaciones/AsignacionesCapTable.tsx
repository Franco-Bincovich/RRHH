"use client"

/**
 * Tabla de asignaciones de capacitación: presentacional. Cubre los cuatro estados del listado
 * (cargando / error / vacío / datos) y no sabe nada de filtros ni de fetch — extraída de
 * AsignacionesTab, que estaba en 211 líneas contra un límite de 150.
 */
import { AlertCircle, Pencil, Trash2 } from "lucide-react"

import { CertificadoCell } from "@/components/features/capacitaciones/CertificadoCell"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Asignacion } from "@/types/capacitacion"

const ESTADO_BADGE: Record<string, "default" | "secondary" | "outline"> = {
  pendiente: "outline", en_curso: "secondary", completado: "default",
}
const ESTADO_LABEL: Record<string, string> = {
  pendiente: "Pendiente", en_curso: "En curso", completado: "Completado",
}

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
    </div>
  )
}

function formatFecha(s: string | null): string {
  if (!s) return "—"
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y}`
}

interface AsignacionesCapTableProps {
  asignaciones: Asignacion[]
  loading: boolean
  error: boolean
  canWrite: boolean
  mostrarEmpresa: boolean
  deletingId: string | null
  onReload: () => void
  onEditarEstado: (a: Asignacion) => void
  onEliminar: (id: string) => void
}

export function AsignacionesCapTable({
  asignaciones, loading, error, canWrite, mostrarEmpresa, deletingId,
  onReload, onEditarEstado, onEliminar,
}: AsignacionesCapTableProps) {
  if (loading) return <TableSkeleton />
  if (error) return <ErrorState action={onReload} />
  if (asignaciones.length === 0) {
    return (
      <EmptyState
        icon={<AlertCircle />} title="Sin asignaciones"
        description="No hay asignaciones que coincidan con los filtros."
      />
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Empleado</TableHead>
          <TableHead>Capacitación</TableHead>
          <TableHead>Estado</TableHead>
          {mostrarEmpresa && <TableHead>Empresa</TableHead>}
          <TableHead>Fecha límite</TableHead>
          <TableHead>Completado</TableHead>
          <TableHead>Certificado</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {asignaciones.map((a) => (
          <TableRow key={a.id}>
            <TableCell className="font-medium">{a.empleado_nombre ?? "—"}</TableCell>
            <TableCell>{a.capacitacion_nombre ?? "—"}</TableCell>
            <TableCell>
              <Badge variant={ESTADO_BADGE[a.estado] ?? "outline"}>{ESTADO_LABEL[a.estado] ?? a.estado}</Badge>
            </TableCell>
            {mostrarEmpresa && <TableCell className="text-muted-foreground">{a.empresa_nombre ?? "—"}</TableCell>}
            <TableCell className="text-muted-foreground">{formatFecha(a.fecha_limite)}</TableCell>
            <TableCell className="text-muted-foreground">{formatFecha(a.fecha_completado)}</TableCell>
            <TableCell>
              <CertificadoCell
                asignacionId={a.id}
                hasCertificado={Boolean(a.certificado_url)}
                canWrite={canWrite}
                onUploaded={onReload}
              />
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-1">
                {canWrite && (
                  <>
                    <Button variant="ghost" size="sm" onClick={() => onEditarEstado(a)} aria-label="Cambiar estado">
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost" size="sm" className="text-destructive hover:text-destructive"
                      disabled={deletingId === a.id} onClick={() => onEliminar(a.id)} aria-label="Eliminar"
                    >
                      {deletingId === a.id ? "..." : <Trash2 className="size-3.5" />}
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
