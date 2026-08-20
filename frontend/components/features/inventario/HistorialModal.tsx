"use client"

import { useEffect, useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { fetchHistorialItem } from "@/services/inventario"
import type { Asignacion, InventarioItem } from "@/types/inventario"

interface Props {
  item: InventarioItem
  onClose: () => void
}

function formatDate(s: string | null) {
  if (!s) return "—"
  const [y,m,d] = s.split("-"); return `${d}/${m}/${y}`
}

export function HistorialModal({ item, onClose }: Props) {
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchHistorialItem(item.id)
      .then((r) => setAsignaciones(r.items))
      .catch(() => setAsignaciones([]))
      .finally(() => setLoading(false))
  }, [item.id])

  return (
    <Dialog open onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Historial — {item.nombre}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          {item.tipo}{item.numero_serie ? ` · ${item.numero_serie}` : ""}
        </p>
        {loading && (
          <div className="space-y-2 mt-2">
            {Array.from({length:3}).map((_,i)=><Skeleton key={i} className="h-10 w-full rounded-lg"/>)}
          </div>
        )}
        {!loading && asignaciones.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">Este ítem no tiene historial de asignaciones.</p>
        )}
        {!loading && asignaciones.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Colaborador</TableHead>
                <TableHead>Desde</TableHead>
                <TableHead>Hasta</TableHead>
                <TableHead>Estado devolución</TableHead>
                <TableHead>Notas</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {asignaciones.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-medium">{a.empleado_nombre ?? "—"}</TableCell>
                  <TableCell>{formatDate(a.fecha_asignacion)}</TableCell>
                  <TableCell>{a.fecha_devolucion ? formatDate(a.fecha_devolucion) : <Badge variant="secondary">Activo</Badge>}</TableCell>
                  <TableCell>{a.estado_devolucion ?? "—"}</TableCell>
                  <TableCell className="text-muted-foreground">{a.notas ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
    </Dialog>
  )
}
