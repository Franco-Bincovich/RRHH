"use client"

import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { CampanaFormFields } from "./CampanaFormFields"
import { useCampanaOpciones } from "./useCampanaOpciones"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { createCampana } from "@/services/assessment"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Campana, CampanaCreate, TipoEval } from "@/types/assessment"

interface CampanaModalProps {
  open: boolean
  onClose: () => void
  onCreated: (campana: Campana) => void
}

export function CampanaModal({ open, onClose, onCreated }: CampanaModalProps) {
  const empresaActivaId = getEmpresaActivaId()

  const [nombre, setNombre]               = useState("")
  const [tipo, setTipo]                   = useState<TipoEval>("completo")
  const [empresaId, setEmpresaId]         = useState<string>(empresaActivaId ?? "")
  const [areaId, setAreaId]               = useState<string>("")
  const [posicionObjetivo, setPosicion]   = useState("")
  const [error, setError]                 = useState<string | null>(null)
  const [loading, setLoading]             = useState(false)

  const { empresas, areas } = useCampanaOpciones(open, empresaActivaId, empresaId, setEmpresaId, setAreaId)

  function handleClose() {
    setNombre("")
    setTipo("completo")
    setEmpresaId(empresaActivaId ?? "")
    setAreaId("")
    setPosicion("")
    setError(null)
    onClose()
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!nombre.trim()) { setError("El nombre es obligatorio."); return }
    if (!empresaId) { setError("Seleccioná una empresa."); return }
    setError(null)
    setLoading(true)
    try {
      const data: CampanaCreate = {
        nombre: nombre.trim(),
        tipo,
        empresa_id: empresaId,
        ...(areaId && { area_id: areaId }),
        ...(posicionObjetivo.trim() && { posicion_objetivo: posicionObjetivo.trim() }),
      }
      const campana = await createCampana(data)
      onCreated(campana)
      handleClose()
    } catch {
      setError("No se pudo crear la campaña. Intentá de nuevo.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) handleClose() }}>
      {/* El ancho (560px) y el alto en `dvh` los pone el patrón, no el modal. */}
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>Nueva campaña de assessment</DialogTitle>
          {/* 🔴 UNA LÍNEA QUE EXPLICA LA CONSECUENCIA, no lo que el modal es (§3). Lo que no se
              deduce de los campos es que crear la campaña NO le avisa a nadie: los links se
              generan y se mandan después, uno por persona, desde la campaña ya creada. */}
          <DialogDescription>
            Crear la campaña no le manda nada a nadie: los links de evaluación se generan después,
            uno por persona.
          </DialogDescription>
        </DialogHeader>

        <form id="campana-form" onSubmit={handleSubmit} className="space-y-4 py-2">
          <CampanaFormFields
            mostrarEmpresa={!empresaActivaId}
            empresas={empresas} empresaId={empresaId} setEmpresaId={setEmpresaId}
            nombre={nombre} setNombre={(v) => { setNombre(v); setError(null) }}
            tipo={tipo} setTipo={setTipo}
            areas={areas} areaId={areaId} setAreaId={setAreaId}
            posicionObjetivo={posicionObjetivo} setPosicion={setPosicion}
            error={error}
          />
        </form>

        <DialogFooter>
          <Button variant="outline" className="min-h-11" onClick={handleClose} disabled={loading}>
            Cancelar
          </Button>
          <Button type="submit" form="campana-form" className="min-h-11" disabled={loading}>
            {loading ? "Creando…" : "Crear campaña"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
