"use client"

import { useEffect, useState } from "react"
import { Search } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { AnalisisResultados } from "./AnalisisResultados"
import { fetchAnalisisPosicion } from "@/services/sucesion"
import type { Area } from "@/types/area"
import type { EmpleadoAnalisis } from "@/types/sucesion"

export function AnalisisAreaModal({
  open, onOpenChange, areas, areaInicial,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  areas: Area[]
  areaInicial: string
}) {
  const [area, setArea]       = useState<string>("")
  const [res, setRes]         = useState<EmpleadoAnalisis[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [ran, setRan]         = useState(false)

  // Al abrir arranca con el área del filtro del mapa y sin resultados previos (igual que antes).
  useEffect(() => {
    if (!open) return
    setArea(areaInicial)
    setRes([])
    setError(null)
    setRan(false)
  }, [open, areaInicial])

  async function handleAnalizar() {
    if (!area) { setError("Seleccioná un área para analizar."); return }
    setLoading(true)
    setError(null)
    setRan(false)
    try {
      const data = await fetchAnalisisPosicion(area)
      setRes(data)
      setRan(true)
    } catch {
      setError("No se pudo obtener el análisis. Intentá de nuevo.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onOpenChange(false) }}>
      {/* El ancho (560px) y el alto en `dvh` los pone el patrón, no el modal: el `max-w-lg`
          escrito a mano quedaba 48px más angosto que el resto de los formularios del sistema. */}
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>Analizar área</DialogTitle>
          {/* 🔴 UNA LÍNEA QUE EXPLICA LA CONSECUENCIA, no lo que el modal es (§3). Lo que no se
              deduce de un selector y un botón es de dónde sale el orden: no es una nota de
              desempeño ni una evaluación, es el score del ASSESSMENT, que muchos no tienen
              rendido — por eso abajo aparecen filas con "Sin score" y quedan al final. */}
          <DialogDescription>
            El ranking usa el score del assessment, no la evaluación de desempeño: quien no lo
            haya rendido aparece sin score.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="analisis-area">Área</Label>
            <Select
              id="analisis-area"
              value={area}
              onChange={(e) => { setArea(e.target.value); setError(null) }}
            >
              <option value="">Seleccioná un área</option>
              {areas.map((a) => (
                <option key={a.id} value={a.id}>{a.nombre}</option>
              ))}
            </Select>
          </div>

          {error && <p className="text-xs text-destructive">{error}</p>}

          {ran && <AnalisisResultados res={res} />}
        </div>

        <DialogFooter>
          <Button variant="outline" className="min-h-11" onClick={() => onOpenChange(false)}>Cerrar</Button>
          <Button
            className="min-h-11 gap-2"
            onClick={handleAnalizar}
            disabled={loading || !area}
          >
            {loading ? "Analizando…" : (
              <><Search className="size-4" />Analizar</>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
