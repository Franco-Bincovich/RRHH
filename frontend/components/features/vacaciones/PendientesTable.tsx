"use client"

import { Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { VacacionPendiente } from "@/types/vacaciones"

interface PendientesTableProps {
  items: VacacionPendiente[]
  canWrite: boolean
  showEmpresa: boolean
  busyId: string | null
  onToggleLiquidada: (p: VacacionPendiente) => void
  onDelete: (id: string) => void
}

/**
 * Días NO tomados. Presentacional. Sin columnas de fecha a propósito: esta entidad no tiene
 * fechas (nadie faltó ningún día), y es exactamente por eso que vive en otra tabla.
 *
 * "Liquidada" se muestra binaria (todos los días pagados o ninguno) porque es lo que la UI
 * ofrece hoy, pero el dato de fondo es un entero: si dias_liquidados queda entre 0 y dias
 * —por un import parcial— se muestra el parcial en vez de mentir con un sí/no.
 */
export function PendientesTable({
  items, canWrite, showEmpresa, busyId, onToggleLiquidada, onDelete,
}: PendientesTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Colaborador</TableHead>
          <TableHead>Área</TableHead>
          {showEmpresa && <TableHead>Empresa</TableHead>}
          <TableHead>Período</TableHead>
          <TableHead>Días</TableHead>
          <TableHead>Liquidada</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((p) => {
          const total = p.dias_liquidados >= p.dias
          const parcial = p.dias_liquidados > 0 && !total
          return (
            <TableRow key={p.id}>
              <TableCell className="font-medium">{p.empleado_nombre ?? "—"}</TableCell>
              <TableCell>{p.area_nombre ?? "—"}</TableCell>
              {showEmpresa && <TableCell>{p.empresa_nombre ?? "—"}</TableCell>}
              <TableCell className="tabular-nums">{p.periodo}</TableCell>
              <TableCell className="tabular-nums">{p.dias}</TableCell>
              <TableCell>
                {parcial ? (
                  <Badge variant="secondary">{p.dias_liquidados} de {p.dias}</Badge>
                ) : (
                  <Badge variant={total ? "default" : "outline"}>{total ? "Sí" : "No"}</Badge>
                )}
              </TableCell>
              <TableCell className="text-right">
                {canWrite && (
                  <div className="flex justify-end gap-1">
                    <Button size="sm" variant="outline" className="min-h-9" disabled={busyId === p.id}
                            onClick={() => onToggleLiquidada(p)}>
                      {total ? "Marcar no liquidada" : "Marcar liquidada"}
                    </Button>
                    <Button size="sm" variant="ghost" className="min-h-9" aria-label="Eliminar"
                            disabled={busyId === p.id} onClick={() => onDelete(p.id)}>
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                )}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
