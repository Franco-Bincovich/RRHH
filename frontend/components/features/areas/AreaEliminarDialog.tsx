"use client"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import type { Area } from "@/types/area"

interface Props {
  area: Area | null
  eliminando: boolean
  onCancel: () => void
  onConfirm: () => void
}

/**
 * Confirmación de baja de un área. Extraído de `areas/page.tsx` (271/150).
 *
 * ⚠️ NO se reemplazó por `components/ui/ConfirmDialog` en la división: eso cambiaría el markup,
 * y el corte tenía que ser un movimiento puro. Unificarlos es una tarea aparte.
 */
export function AreaEliminarDialog({ area, eliminando, onCancel, onConfirm }: Props) {
  return (
    <Dialog open={Boolean(area)} onOpenChange={(o) => { if (!o) onCancel() }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Eliminar área</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          ¿Estás seguro de que querés eliminar{" "}
          <span className="font-medium text-foreground">{area?.nombre}</span>?
          Esta acción no se puede deshacer.
        </p>
        <DialogFooter>
          <Button
            variant="outline"
            className="min-h-11"
            onClick={onCancel}
            disabled={eliminando}
          >
            Cancelar
          </Button>
          <Button
            variant="destructive"
            className="min-h-11"
            onClick={onConfirm}
            disabled={eliminando}
          >
            {eliminando ? "Eliminando..." : "Eliminar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
