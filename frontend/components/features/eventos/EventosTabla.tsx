"use client"

import { Check, Pencil, RotateCcw, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { Evento } from "@/types/evento"

/**
 * 🔴 EL `T00:00:00` NO ES DECORATIVO. `new Date("2026-10-01")` parsea como UTC medianoche, y en
 * Argentina (UTC-3) eso se renderiza como el 30/09: la agenda mostraría todos los eventos un día
 * antes. Con la hora explícita el string se interpreta como local. Misma función y mismo motivo
 * que en `proyectos/HorasTab.tsx`; el repo todavía no tiene un formateador compartido.
 */
function formatFecha(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(
    "es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

interface Props {
  eventos: Evento[]
  canWrite: boolean
  onEdit: (e: Evento) => void
  onDelete: (e: Evento) => void
  onResuelta: (e: Evento, resuelta: boolean) => void
}

/**
 * Tabla de la agenda. PRESENTACIONAL: sin estado, sin fetch, sin efectos.
 *
 * ⚠️ Los botones de escritura se OMITEN cuando `canWrite` es false, no se deshabilitan. Un
 * `disabled` sobre el `Button` de shadcn no se puede afirmar en un test —el markup trae la clase
 * `disabled:...` de Tailwind SIEMPRE— y además un botón muerto invita a clickearlo. Es la regla
 * que dejó escrita `ClientesTabla`.
 *
 * 🔑 El botón de resolver cambia de ICONO Y DE ETIQUETA según el estado, y llama al MISMO
 * handler con el valor que quiere. No hay dos acciones: resolver es reversible, y el front manda
 * el estado deseado en vez de un incremento sobre uno que puede estar viejo.
 */
export function EventosTabla({ eventos, canWrite, onEdit, onDelete, onResuelta }: Props) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Evento</TableHead>
          <TableHead>Fecha</TableHead>
          <TableHead>Aviso</TableHead>
          <TableHead>Visibilidad</TableHead>
          <TableHead>Estado</TableHead>
          {canWrite && <TableHead className="w-32 text-right">Acciones</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {eventos.map((e) => (
          <TableRow key={e.id}>
            <TableCell className="font-medium">
              {e.nombre}
              {e.descripcion && (
                <p className="text-xs font-normal text-muted-foreground">{e.descripcion}</p>
              )}
            </TableCell>
            <TableCell className="tabular-nums">{formatFecha(e.fecha)}</TableCell>
            <TableCell className="tabular-nums">{e.dias_aviso} días antes</TableCell>
            <TableCell>
              <Badge variant={e.es_publica ? "default" : "secondary"}>
                {e.es_publica ? "Del equipo" : "Privado"}
              </Badge>
            </TableCell>
            <TableCell>
              {e.resuelta ? (
                <Badge variant="secondary">
                  Resuelto{e.resuelta_por_nombre ? ` por ${e.resuelta_por_nombre}` : ""}
                </Badge>
              ) : (
                <Badge variant="outline">Pendiente</Badge>
              )}
            </TableCell>
            {canWrite && (
              <TableCell className="text-right">
                <Button
                  variant="ghost" size="icon"
                  aria-label={`${e.resuelta ? "Reabrir" : "Resolver"} ${e.nombre}`}
                  onClick={() => onResuelta(e, !e.resuelta)}
                >
                  {e.resuelta ? <RotateCcw className="size-4" /> : <Check className="size-4" />}
                </Button>
                <Button variant="ghost" size="icon" aria-label={`Editar ${e.nombre}`}
                        onClick={() => onEdit(e)}>
                  <Pencil className="size-4" />
                </Button>
                <Button variant="ghost" size="icon" aria-label={`Eliminar ${e.nombre}`}
                        onClick={() => onDelete(e)}>
                  <Trash2 className="size-4" />
                </Button>
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
