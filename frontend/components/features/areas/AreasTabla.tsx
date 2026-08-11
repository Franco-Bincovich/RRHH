"use client"

import { Pencil, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { Area } from "@/types/area"

interface Props {
  areas: Area[]
  canWrite: boolean
  onEdit: (a: Area) => void
  onDelete: (a: Area) => void
}

/**
 * Tabla de áreas. PRESENTACIONAL: sin estado, sin fetch, sin efectos.
 *
 * Existe como componente aparte para que `areas/page.tsx` bajara de 271/150. Molde:
 * `ClientesTabla.tsx`, que se escribió justamente copiando la estructura de esta pantalla
 * y NO su tamaño.
 *
 * ⚠️ Los botones de escritura se OMITEN cuando `canWrite` es false, no se deshabilitan: un
 * `disabled` sobre el Button de shadcn no se puede afirmar en un test (la clase `disabled:`
 * viaja siempre) y además un botón muerto invita a clickearlo.
 */
export function AreasTabla({ areas, canWrite, onEdit, onDelete }: Props) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Nombre</TableHead>
          <TableHead>Descripción</TableHead>
          <TableHead>Responsable</TableHead>
          <TableHead className="text-right">Empleados</TableHead>
          <TableHead className="w-24 text-right">Acciones</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {areas.map((area) => (
          <TableRow key={area.id}>
            <TableCell className="font-medium">{area.nombre}</TableCell>
            <TableCell className="text-muted-foreground">
              {area.descripcion ?? <span className="italic text-muted-foreground/60">—</span>}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {area.responsable_nombre ?? <span className="italic text-muted-foreground/60">—</span>}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {area.cantidad_empleados}
            </TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-1">
                {canWrite && (
                  <>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-9"
                      aria-label={`Editar ${area.nombre}`}
                      onClick={() => onEdit(area)}
                    >
                      <Pencil className="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-9 text-destructive hover:text-destructive"
                      aria-label={`Eliminar ${area.nombre}`}
                      onClick={() => onDelete(area)}
                    >
                      <Trash2 className="size-4" />
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
