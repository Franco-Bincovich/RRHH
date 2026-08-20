"use client"

import { useEffect, useState } from "react"
import { Search } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { NIVEL_BADGE_CLASS } from "./_sucesion_ui"
import { fetchAnalisisPosicion } from "@/services/sucesion"
import type { Area } from "@/types/area"
import type { EmpleadoAnalisis } from "@/types/sucesion"

function nivelBadge(nivel: string | null) {
  if (!nivel) return null
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${NIVEL_BADGE_CLASS[nivel] ?? "bg-muted text-muted-foreground"}`}>
      {nivel}
    </span>
  )
}

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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Analizar área</DialogTitle>
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

          {ran && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground">
                {res.length === 0
                  ? "No hay colaboradores en esta área."
                  : `${res.length} colaborador${res.length !== 1 ? "es" : ""} encontrado${res.length !== 1 ? "s" : ""}`}
              </p>
              {res.length > 0 && (
                <ul className="max-h-64 divide-y divide-border overflow-y-auto rounded-lg border">
                  {res.map((emp, idx) => (
                    <li key={emp.id} className="flex items-center gap-3 px-3 py-2.5">
                      <span className="w-5 shrink-0 text-center text-xs font-semibold text-muted-foreground">
                        {idx + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">
                          {emp.nombre} {emp.apellido}
                        </p>
                        {emp.cargo && (
                          <p className="truncate text-xs text-muted-foreground">{emp.cargo}</p>
                        )}
                      </div>
                      <div className="flex shrink-0 items-center gap-1.5">
                        {emp.score != null
                          ? <Badge variant="default" className="tabular-nums">{emp.score}</Badge>
                          : <Badge variant="outline">Sin score</Badge>
                        }
                        {nivelBadge(emp.potencial)}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
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
