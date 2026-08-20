/**
 * Tabla de ausencias, presentacional. Dueña de los estados de carga/error/vacío y del
 * formato de fecha. Sin lógica de negocio ni fetch: la página le pasa datos y callbacks.
 */
import { AlertCircle, Pencil, Paperclip, Trash2 } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { Ausencia } from "@/types/ausencias"

interface AusenciasTableProps {
  items: Ausencia[]
  loading: boolean
  error: boolean
  showEmpresa: boolean
  canWrite: boolean
  deletingId: string | null
  onRetry: () => void
  onEdit: (a: Ausencia) => void
  onDelete: (id: string) => void
  onDocs: (a: Ausencia) => void
}

function formatFecha(s: string): string {
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y}`
}

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}

export function AusenciasTable({
  items, loading, error, showEmpresa, canWrite, deletingId, onRetry, onEdit, onDelete, onDocs,
}: AusenciasTableProps) {
  if (loading) return <TableSkeleton />
  if (error) return <ErrorState action={onRetry} />
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<AlertCircle />}
        title="Sin ausencias"
        description="No hay registros de ausencias que coincidan con los filtros."
      />
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Colaborador</TableHead>
          <TableHead>Área</TableHead>
          {showEmpresa && <TableHead>Empresa</TableHead>}
          <TableHead>Tipo</TableHead>
          <TableHead>Desde</TableHead>
          <TableHead>Hasta</TableHead>
          <TableHead>Días</TableHead>
          <TableHead>Justificada</TableHead>
          <TableHead>Motivo</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((a) => (
          <TableRow key={a.id}>
            <TableCell className="font-medium">{a.empleado_nombre ?? "—"}</TableCell>
            <TableCell className="text-muted-foreground">{a.area_nombre ?? "—"}</TableCell>
            {showEmpresa && <TableCell className="text-muted-foreground">{a.empresa_nombre ?? "—"}</TableCell>}
            <TableCell>{a.tipo_nombre ?? "—"}</TableCell>
            <TableCell>{formatFecha(a.fecha_desde)}</TableCell>
            <TableCell>{formatFecha(a.fecha_hasta)}</TableCell>
            <TableCell>{a.dias}</TableCell>
            <TableCell>
              <Badge variant={a.justificada ? "secondary" : "outline"}>
                {a.justificada ? "Sí" : "No"}
              </Badge>
            </TableCell>
            <TableCell className="max-w-[200px] truncate text-muted-foreground text-sm">
              {a.motivo ?? "—"}
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="sm" onClick={() => onDocs(a)} aria-label="Documentos">
                  <Paperclip className="size-3.5" />
                </Button>
                {canWrite && (
                  <>
                    <Button variant="ghost" size="sm" onClick={() => onEdit(a)} aria-label="Editar">
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      disabled={deletingId === a.id}
                      onClick={() => onDelete(a.id)}
                      aria-label="Eliminar"
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
