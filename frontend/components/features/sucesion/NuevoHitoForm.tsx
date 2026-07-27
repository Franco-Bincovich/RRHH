"use client"

import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { createHito } from "@/services/sucesion"
import type { Hito } from "@/types/sucesion"

// Form inline de alta de hito, dentro del panel de detalle. Se monta recién al abrirlo, así que
// su estado arranca limpio en cada apertura (antes lo reseteaba a mano el padre).
export function NuevoHitoForm({
  planId, onCreado, onCancelar,
}: {
  planId: string
  onCreado: (hito: Hito) => void
  onCancelar: () => void
}) {
  const [form, setForm]       = useState({ titulo: "", descripcion: "", fecha_objetivo: "" })
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)

  async function handleSubmit() {
    if (!form.titulo.trim()) { setError("El título es requerido."); return }
    setLoading(true)
    setError(null)
    try {
      const hito = await createHito(planId, {
        titulo: form.titulo.trim(),
        descripcion: form.descripcion.trim() || undefined,
        fecha_objetivo: form.fecha_objetivo || undefined,
      })
      onCreado(hito)
      onCancelar()
    } catch {
      setError("No se pudo agregar el hito. Intentá de nuevo.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-xl border bg-muted/30 p-4 space-y-3">
      <div className="space-y-1.5">
        <Label htmlFor="hito-titulo">
          Título <span className="text-destructive" aria-hidden>*</span>
        </Label>
        <Input
          id="hito-titulo"
          value={form.titulo}
          onChange={(e) => { setForm((p) => ({ ...p, titulo: e.target.value })); setError(null) }}
          placeholder="Ej. Completar curso de liderazgo"
          autoFocus
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="hito-desc">
          Descripción <span className="text-muted-foreground">(opcional)</span>
        </Label>
        <Input
          id="hito-desc"
          value={form.descripcion}
          onChange={(e) => setForm((p) => ({ ...p, descripcion: e.target.value }))}
          placeholder="Detalles del hito…"
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="hito-fecha">
          Fecha objetivo <span className="text-muted-foreground">(opcional)</span>
        </Label>
        <Input
          id="hito-fecha"
          type="date"
          value={form.fecha_objetivo}
          onChange={(e) => setForm((p) => ({ ...p, fecha_objetivo: e.target.value }))}
        />
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="outline"
          className="min-h-8 flex-1"
          onClick={onCancelar}
          disabled={loading}
        >
          Cancelar
        </Button>
        <Button
          size="sm"
          className="min-h-8 flex-1"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? "Guardando…" : "Agregar hito"}
        </Button>
      </div>
    </div>
  )
}
