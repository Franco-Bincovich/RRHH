"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { AdjuntosSection } from "./AdjuntosSection"

interface Props {
  open: boolean
  onClose: () => void
  entidad: string
  entidadId: string
  titulo: string
}

/**
 * Envoltorio en modal de <AdjuntosSection> para las pantallas de listado (vacaciones,
 * ausencias, offboarding) que no tienen ficha de detalle. Reusa exactamente el mismo
 * componente de adjuntos del legajo; solo lo abre sobre un registro puntual. El título
 * del diálogo describe el registro; la tarjeta interna conserva su encabezado "Documentos".
 */
export function AdjuntosDialog({ open, onClose, entidad, entidadId, titulo }: Props) {
  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
        </DialogHeader>
        {entidadId && <AdjuntosSection entidad={entidad} entidadId={entidadId} />}
      </DialogContent>
    </Dialog>
  )
}
