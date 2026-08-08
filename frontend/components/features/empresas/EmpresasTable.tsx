"use client"

import Link from "next/link"
import { Pencil, Power, PowerOff } from "lucide-react"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import type { Empresa } from "@/types/empresa"

interface EmpresasTableProps {
  empresas: Empresa[]
  canWrite: boolean
  onEdit: (empresa: Empresa) => void
  onToggle: (empresa: Empresa) => void
  togglingId: string | null
}

/** Guion para un valor vacío: una celda en blanco no distingue "sin dato" de "no cargó". */
function Vacio() {
  return <span className="italic text-muted-foreground/60">—</span>
}

/**
 * Tabla de empresas con edición y toggle de activa por fila (solo canWrite).
 *
 * Extraída de app/(dashboard)/empresas/page.tsx, que estaba en 204/150 y no admitía el menú de
 * export sin empeorar la deuda. Presentacional: sin estado ni fetch. Molde: UsuariosTable.tsx.
 */
export function EmpresasTable({ empresas, canWrite, onEdit, onToggle, togglingId }: EmpresasTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Nombre</TableHead>
          <TableHead>CUIT</TableHead>
          <TableHead>Email</TableHead>
          <TableHead>Estado</TableHead>
          <TableHead className="w-28 text-right">Acciones</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {empresas.map((empresa) => (
          <TableRow key={empresa.id}>
            <TableCell className="font-medium">
              <Link href={`/empresas/${empresa.id}`} className="hover:underline hover:text-primary">
                {empresa.nombre}
              </Link>
            </TableCell>
            <TableCell className="font-mono text-sm text-muted-foreground">
              {empresa.cuit ?? <Vacio />}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {empresa.email ?? <Vacio />}
            </TableCell>
            <TableCell>
              <Badge variant={empresa.activa ? "default" : "secondary"}>
                {empresa.activa ? "Activa" : "Inactiva"}
              </Badge>
            </TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-1">
                {canWrite && (
                  <>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-9"
                      aria-label={`Editar ${empresa.nombre}`}
                      onClick={() => onEdit(empresa)}
                    >
                      <Pencil className="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-9"
                      aria-label={empresa.activa ? `Desactivar ${empresa.nombre}` : `Activar ${empresa.nombre}`}
                      onClick={() => onToggle(empresa)}
                      disabled={togglingId === empresa.id}
                    >
                      {empresa.activa ? <PowerOff className="size-4" /> : <Power className="size-4" />}
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
