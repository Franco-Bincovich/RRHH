"use client"

import { Pencil, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { Cliente } from "@/types/cliente"

interface Props {
  clientes: Cliente[]
  canWrite: boolean
  onEdit: (c: Cliente) => void
  onDelete: (c: Cliente) => void
}

/**
 * Tabla del catálogo de clientes. PRESENTACIONAL: sin estado, sin fetch, sin efectos.
 *
 * Existe como componente aparte para que `clientes/page.tsx` no repita el molde de
 * `areas/page.tsx`, que está en 271/150 justamente por tener el orquestador y la tabla en el
 * mismo archivo. La estructura es la de áreas; el tamaño, no.
 *
 * ⚠️ Los botones de escritura se OMITEN cuando `canWrite` es false, no se deshabilitan. Un
 * `disabled` sobre el `Button` de shadcn no se puede afirmar en un test —el markup trae la
 * clase `disabled:...` de Tailwind SIEMPRE, así que `not.toContain("disabled")` pasa con el
 * guard borrado— y además un botón muerto invita a clickearlo. Ver ClientesTabla.test.tsx.
 */
export function ClientesTabla({ clientes, canWrite, onEdit, onDelete }: Props) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Cliente</TableHead>
          <TableHead>Estado</TableHead>
          {canWrite && <TableHead className="w-24 text-right">Acciones</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {clientes.map((c) => (
          <TableRow key={c.id}>
            <TableCell className="font-medium">{c.nombre}</TableCell>
            <TableCell>
              <Badge variant={c.activo ? "default" : "secondary"}>
                {c.activo ? "Activo" : "Dado de baja"}
              </Badge>
            </TableCell>
            {canWrite && (
              <TableCell className="text-right">
                <Button variant="ghost" size="icon" aria-label={`Editar ${c.nombre}`}
                        onClick={() => onEdit(c)}>
                  <Pencil className="size-4" />
                </Button>
                {c.activo && (
                  <Button variant="ghost" size="icon" aria-label={`Dar de baja ${c.nombre}`}
                          onClick={() => onDelete(c)}>
                    <Trash2 className="size-4" />
                  </Button>
                )}
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
