"use client"

import { useEffect, useState } from "react"

import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { actualizarCesion, crearCesion } from "@/services/cesiones"
import type { Cesion } from "@/types/cesion"
import { avisarGuardado } from "@/components/features/shared/avisoGuardado"

interface Props {
  open: boolean
  empleadoId: string
  cesion: Cesion | null // null = crear · objeto = editar
  onClose: () => void
  onSuccess: () => void
}

/** Form de alta/edición de una cesión: fecha + empresa (texto libre). */
export function CesionModal({ open, empleadoId, cesion, onClose, onSuccess }: Props) {
  const [fecha, setFecha] = useState("")
  const [empresa, setEmpresa] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!open) return
    setFecha(cesion?.fecha ?? "")
    setEmpresa(cesion?.empresa_cesion ?? "")
    setError("")
  }, [open, cesion])

  async function handleSave() {
    if (!fecha || !empresa.trim()) {
      setError("Completá la fecha y la empresa.")
      return
    }
    setSaving(true)
    setError("")
    try {
      const data = { fecha, empresa_cesion: empresa.trim() }
      if (cesion) await actualizarCesion(cesion.id, data)
      else await crearCesion(empleadoId, data)
      avisarGuardado("Cesión", "f", Boolean(cesion))
      onSuccess()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "No se pudo guardar la cesión.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{cesion ? "Editar cesión" : "Agregar cesión"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="cesion-fecha">Fecha</Label>
            <Input id="cesion-fecha" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="cesion-empresa">Empresa</Label>
            <Input
              id="cesion-empresa"
              value={empresa}
              placeholder="Empresa donde estuvo cedido"
              onChange={(e) => setEmpresa(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button type="button" className="min-h-11" onClick={handleSave} disabled={saving}>
            {saving ? "Guardando..." : cesion ? "Guardar" : "Agregar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
