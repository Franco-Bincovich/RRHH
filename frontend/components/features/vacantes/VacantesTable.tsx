"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import type { EstadoVacante, Vacante } from "@/types/vacantes"

/**
 * Los MISMOS textos que emite el export (`services/_vacantes_export.py::_ESTADO_LABEL`).
 * Si divergen, la pantalla y el archivo llaman distinto al mismo estado.
 */
const ESTADO_LABELS: Record<EstadoVacante, string> = {
  nueva: "Nueva",
  en_proceso: "En proceso",
  con_candidatos: "Con candidatos",
  cerrada: "Cerrada",
}

const ESTADO_VARIANTS: Record<EstadoVacante, "default" | "secondary" | "destructive" | "outline"> = {
  nueva: "outline",
  en_proceso: "default",
  con_candidatos: "secondary",
  cerrada: "destructive",
}

function formatFecha(raw: string | null): string {
  if (!raw) return "—"
  const d = new Date(raw)
  return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

interface VacantesTableProps {
  vacantes: Vacante[]
  /** En modo consolidado se agrega la columna Empresa: sin ella no se sabe de cuál es cada una. */
  mostrarEmpresa: boolean
  onAbrir: (id: string) => void
}

/**
 * Tabla de vacantes, con la fila entera como link al detalle.
 *
 * Extraída de app/(dashboard)/vacantes/page.tsx, que estaba en 217/150 y no admitía el menú de
 * export sin empeorar la deuda. Presentacional: sin estado ni fetch. Molde: EmpresasTable.tsx.
 */
export function VacantesTable({ vacantes, mostrarEmpresa, onAbrir }: VacantesTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Título</TableHead>
          {mostrarEmpresa && <TableHead>Empresa</TableHead>}
          <TableHead>Área</TableHead>
          <TableHead>Estado</TableHead>
          <TableHead>Fecha de apertura</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {vacantes.map((vacante) => (
          <TableRow key={vacante.id} className="cursor-pointer" onClick={() => onAbrir(vacante.id)}>
            <TableCell className="font-medium">{vacante.titulo}</TableCell>
            {mostrarEmpresa && (
              <TableCell className="text-muted-foreground">{vacante.empresa_nombre ?? "—"}</TableCell>
            )}
            <TableCell className="text-muted-foreground">{vacante.area_nombre ?? "—"}</TableCell>
            <TableCell>
              <Badge variant={ESTADO_VARIANTS[vacante.estado]}>{ESTADO_LABELS[vacante.estado]}</Badge>
            </TableCell>
            <TableCell className="text-muted-foreground">
              {formatFecha(vacante.fecha_apertura ?? vacante.created_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
