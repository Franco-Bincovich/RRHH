"use client"

/**
 * Tabla del catálogo de ítems de inventario: presentacional. Cubre los cuatro estados del
 * listado (cargando / error / vacío / datos) y no sabe nada de filtros ni de fetch — extraída
 * de ItemsTab, que estaba en 152 contra un límite de 150.
 *
 * Molde: AsignacionesInvTable.tsx, la tabla de la pestaña hermana.
 *
 * `deletingId` entra por prop y no es estado propio: el borrado lo dispara y lo reintenta el
 * orquestador, que es quien tiene el service y el toast de error.
 */
import { AlertCircle, History, Pencil, Trash2 } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { InventarioItem } from "@/types/inventario"

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

interface ItemsInvTableProps {
  items: InventarioItem[]
  loading: boolean
  error: boolean
  canWrite: boolean
  mostrarEmpresa: boolean
  deletingId: string | null
  onReload: () => void
  onHistorial: (item: InventarioItem) => void
  onEditar: (item: InventarioItem) => void
  onEliminar: (id: string) => void
}

export function ItemsInvTable({
  items, loading, error, canWrite, mostrarEmpresa, deletingId,
  onReload, onHistorial, onEditar, onEliminar,
}: ItemsInvTableProps) {
  if (loading) return <Skeleton5 />
  if (error) return <ErrorState action={onReload} />
  if (items.length === 0) {
    return (
      <EmptyState icon={<AlertCircle />} title="Sin ítems" description="No hay ítems de inventario para los filtros seleccionados." />
    )
  }

  return (
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
                <Button variant="ghost" size="sm" onClick={() => onHistorial(item)} aria-label="Historial"><History className="size-3.5" /></Button>
                {canWrite && (
                  <>
                    <Button variant="ghost" size="sm" onClick={() => onEditar(item)} aria-label="Editar"><Pencil className="size-3.5" /></Button>
                    <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" disabled={deletingId === item.id} onClick={() => onEliminar(item.id)} aria-label="Eliminar">
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
  )
}
