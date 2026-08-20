/**
 * Tabla de la vista "lista" de vacaciones, presentacional. Sin lógica de negocio ni fetch.
 * Los estados de carga/error/vacío quedan en la página porque se comparten con la vista
 * "mapa"; este componente asume que ya hay filas para mostrar.
 */
import { Paperclip } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { EstadoVacacion, SolicitudVacaciones } from "@/types/vacaciones"

const ESTADO_LABELS: Record<EstadoVacacion, string> = {
  planificada: "Planificada",
  tomada: "Tomada",
  cancelada: "Cancelada",
}

const ESTADO_VARIANTS: Record<EstadoVacacion, "default" | "secondary" | "outline" | "destructive"> = {
  planificada: "default",
  tomada: "secondary",
  cancelada: "destructive",
}

// Null-safe aunque hoy fecha_desde/fecha_hasta sean NOT NULL en la DB: si alguna vez llegara
// un null, `s.split` tumbaría la tabla entera. Mismo molde que AsignacionesCapTable.
function formatFecha(s: string | null): string {
  if (!s) return "—"
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y}`
}

interface VacacionesTableProps {
  items: SolicitudVacaciones[]
  canWrite: boolean
  showEmpresa: boolean
  cancelingId: string | null
  onCancel: (id: string) => void
  onDocs: (s: SolicitudVacaciones) => void
}

export function VacacionesTable({
  items, canWrite, showEmpresa, cancelingId, onCancel, onDocs,
}: VacacionesTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Colaborador</TableHead>
          <TableHead>Área</TableHead>
          {showEmpresa && <TableHead>Empresa</TableHead>}
          <TableHead>Desde</TableHead>
          <TableHead>Hasta</TableHead>
          <TableHead>Días</TableHead>
          <TableHead>Estado</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((s) => (
          <TableRow key={s.id}>
            <TableCell className="font-medium">{s.empleado_nombre ?? "—"}</TableCell>
            <TableCell className="text-muted-foreground">{s.area_nombre ?? "—"}</TableCell>
            {showEmpresa && <TableCell className="text-muted-foreground">{s.empresa_nombre ?? "—"}</TableCell>}
            <TableCell>{formatFecha(s.fecha_desde)}</TableCell>
            <TableCell>{formatFecha(s.fecha_hasta)}</TableCell>
            <TableCell>{s.dias}</TableCell>
            <TableCell>
              <Badge variant={ESTADO_VARIANTS[s.estado]}>{ESTADO_LABELS[s.estado]}</Badge>
            </TableCell>
            <TableCell>
              <div className="flex items-center justify-end gap-1">
                <Button variant="ghost" size="sm" onClick={() => onDocs(s)} aria-label="Documentos">
                  <Paperclip className="size-3.5" />
                </Button>
                {canWrite && s.estado !== "cancelada" && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    disabled={cancelingId === s.id}
                    onClick={() => onCancel(s.id)}
                  >
                    {cancelingId === s.id ? "Cancelando..." : "Cancelar"}
                  </Button>
                )}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
