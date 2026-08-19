"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Lock } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { cerrarPeriodo, MODULO_LABEL } from "@/services/periodos"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Empresa } from "@/types/empresa"

/** Formulario para cerrar un período nuevo. Al confirmar refresca la lista (onCreated). */
export function PeriodoForm({ onCreated }: { onCreated: () => void }) {
  const activa = getEmpresaActivaId()
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empresaId, setEmpresaId] = useState(activa && activa !== "todas" ? activa : "")
  const [modulo, setModulo] = useState("")
  const [desde, setDesde] = useState("")
  const [hasta, setHasta] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    fetchEmpresas()
      .then((r) => setEmpresas(r.items.filter((e) => e.activa)))
      .catch(() => setEmpresas([]))
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!empresaId) return setError("Elegí una empresa")
    if (!desde || !hasta) return setError("Completá las fechas de inicio y fin")
    if (hasta < desde) return setError("La fecha de fin debe ser igual o posterior al inicio")
    setSaving(true)
    setError("")
    try {
      await cerrarPeriodo({ empresa_id: empresaId, modulo: modulo || null, desde, hasta })
      toast.success("Período cerrado")
      setDesde("")
      setHasta("")
      setModulo("")
      onCreated()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "No se pudo cerrar el período")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card as="form" onSubmit={handleSubmit}>
      <h2 className="mb-1 text-base font-semibold text-foreground">Cerrar un período</h2>
      <p className="mb-4 text-sm text-muted-foreground">
        Cerrar un período impide cargar, editar o borrar registros con fecha dentro de ese rango.
      </p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <Label htmlFor="periodo-empresa">Empresa</Label>
          <Select id="periodo-empresa" value={empresaId} onChange={(e) => setEmpresaId(e.target.value)}>
            <option value="">Elegí una empresa</option>
            {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="periodo-modulo">Módulo</Label>
          <Select id="periodo-modulo" value={modulo} onChange={(e) => setModulo(e.target.value)}>
            <option value="">Todos los módulos</option>
            {Object.entries(MODULO_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="periodo-desde">Desde</Label>
          <Input id="periodo-desde" type="date" className="h-11" value={desde} onChange={(e) => setDesde(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="periodo-hasta">Hasta</Label>
          <Input id="periodo-hasta" type="date" className="h-11" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </div>
      </div>
      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      <Button type="submit" className="mt-4 min-h-11 gap-2" disabled={saving}>
        <Lock className="size-4" />
        {saving ? "Cerrando..." : "Cerrar período"}
      </Button>
    </Card>
  )
}
