"use client"

import { useState } from "react"

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Select } from "@/components/ui/select"
import { iniciarOffboarding } from "@/services/offboarding"
import type { MotivoEgreso } from "@/types/offboarding"

const MOTIVOS_OFFBOARDING: { label: string; value: MotivoEgreso }[] = [
  { label: "Renuncia", value: "renuncia" },
  { label: "Desvinculación", value: "despido" },
  { label: "Fin de contrato", value: "fin_contrato" },
]

interface OffboardingModalProps {
  open: boolean
  empleadoId: string
  onClose: () => void
  onSuccess: () => void
}

/** Modal para iniciar el offboarding de un empleado activo eligiendo el motivo de egreso. */
export function OffboardingModal({ open, empleadoId, onClose, onSuccess }: OffboardingModalProps) {
  const [motivo, setMotivo] = useState<MotivoEgreso>("renuncia")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleConfirmar() {
    setLoading(true)
    setError(null)
    try {
      await iniciarOffboarding({ empleado_id: empleadoId, motivo })
      onSuccess()
    } catch {
      setError("No se pudo iniciar el offboarding. Verificá si ya tiene uno activo.")
    } finally {
      setLoading(false)
    }
  }

  function handleOpenChange(open: boolean) {
    if (!open) {
      setMotivo("renuncia")
      setError(null)
      onClose()
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Iniciar offboarding</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="motivo-egreso">Motivo de egreso</Label>
            <Select
              id="motivo-egreso"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value as MotivoEgreso)}
            >
              {MOTIVOS_OFFBOARDING.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </Select>
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading} className="min-h-11">
            Cancelar
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirmar}
            disabled={loading}
            className="min-h-11"
          >
            {loading ? "Iniciando…" : "Confirmar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
