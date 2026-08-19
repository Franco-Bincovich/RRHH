"use client"

import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { fetchAreas } from "@/services/areas"
import { createCampana } from "@/services/assessment"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Area } from "@/types/area"
import type { Campana, CampanaCreate, TipoEval } from "@/types/assessment"
import type { Empresa } from "@/types/empresa"

interface CampanaModalProps {
  open: boolean
  onClose: () => void
  onCreated: (campana: Campana) => void
}

const TIPOS: { value: TipoEval; label: string }[] = [
  { value: "completo",   label: "Completo (AREAS + Cognitivo + Técnico)" },
  { value: "conductual", label: "Conductual (AREAS)" },
  { value: "cognitivo",  label: "Cognitivo" },
]

export function CampanaModal({ open, onClose, onCreated }: CampanaModalProps) {
  const empresaActivaId = getEmpresaActivaId()

  const [nombre, setNombre]               = useState("")
  const [tipo, setTipo]                   = useState<TipoEval>("completo")
  const [empresaId, setEmpresaId]         = useState<string>(empresaActivaId ?? "")
  const [areaId, setAreaId]               = useState<string>("")
  const [posicionObjetivo, setPosicion]   = useState("")
  const [empresas, setEmpresas]           = useState<Empresa[]>([])
  const [areas, setAreas]                 = useState<Area[]>([])
  const [error, setError]                 = useState<string | null>(null)
  const [loading, setLoading]             = useState(false)

  useEffect(() => {
    if (!open) return
    // Solo cargar empresas cuando topbar = "Todas"
    if (!empresaActivaId) {
      fetchEmpresas()
        .then((res) => {
          const activas = res.items.filter((e) => e.activa)
          setEmpresas(activas)
          if (activas.length > 0 && !empresaId) setEmpresaId(activas[0].id)
        })
        .catch(() => {})
    }
    // Cargar áreas filtradas por empresa activa (apiFetch envía X-Empresa-Id automáticamente)
    fetchAreas()
      .then(setAreas)
      .catch(() => setAreas([]))
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  // Cuando cambia la empresa seleccionada, recargar las áreas de esa empresa
  useEffect(() => {
    if (!open || empresaActivaId) return
    if (!empresaId) { setAreas([]); return }
    fetchAreas(empresaId)
      .then(setAreas)
      .catch(() => setAreas([]))
    setAreaId("")
  }, [empresaId]) // eslint-disable-line react-hooks/exhaustive-deps

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
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nueva campaña de assessment</DialogTitle>
        </DialogHeader>

        <form id="campana-form" onSubmit={handleSubmit} className="space-y-4 py-2">
          {/* Selector de empresa — solo cuando topbar = "Todas" */}
          {!empresaActivaId && (
            <div className="space-y-1.5">
              <Label htmlFor="campana-empresa">Empresa</Label>
              <Select
                id="campana-empresa"
                value={empresaId}
                onChange={(e) => setEmpresaId(e.target.value)}
              >
                <option value="">Seleccioná una empresa…</option>
                {empresas.map((e) => (
                  <option key={e.id} value={e.id}>{e.nombre}</option>
                ))}
              </Select>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="campana-nombre">Nombre</Label>
            <Input
              id="campana-nombre"
              value={nombre}
              onChange={(e) => { setNombre(e.target.value); setError(null) }}
              placeholder="Ej. Assessment Q2 2025"
              autoFocus
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="campana-tipo">Tipo de evaluación</Label>
            <Select
              id="campana-tipo"
              value={tipo}
              onChange={(e) => setTipo(e.target.value as TipoEval)}
            >
              {TIPOS.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="campana-area">Área <span className="text-muted-foreground">(opcional)</span></Label>
            <Select
              id="campana-area"
              value={areaId}
              onChange={(e) => setAreaId(e.target.value)}
            >
              <option value="">Sin área específica</option>
              {areas.map((a) => (
                <option key={a.id} value={a.id}>{a.nombre}</option>
              ))}
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="campana-posicion">
              Posición objetivo <span className="text-muted-foreground">(opcional)</span>
            </Label>
            <Input
              id="campana-posicion"
              value={posicionObjetivo}
              onChange={(e) => setPosicion(e.target.value)}
              placeholder="Ej. Tech Lead, Product Manager…"
            />
          </div>

          {error && (
            <p className="text-xs text-destructive">{error}</p>
          )}
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
