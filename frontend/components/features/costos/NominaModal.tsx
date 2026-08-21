"use client"

import { useCallback, useEffect, useState } from "react"
import { Loader2 } from "lucide-react"

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Select } from "@/components/ui/select"
import { cargarNomina } from "@/services/costos"
import { fetchEmpleados } from "@/services/empleados"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Empleado } from "@/types/empleado"

const MESES_LARGOS = [
  "Enero","Febrero","Marzo","Abril","Mayo","Junio",
  "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre",
]
const ANIOS = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i)

interface NominaRow {
  bruto: string
  neto: string
}

export interface NominaModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export function NominaModal({ open, onClose, onSuccess }: NominaModalProps) {
  const now = new Date()
  const empresaActivaId = typeof window !== "undefined" ? getEmpresaActivaId() : null
  const [mes, setMes] = useState(now.getMonth() + 1)
  const [anio, setAnio] = useState(now.getFullYear())
  const [empleados, setEmpleados] = useState<Empleado[]>([])
  const [rows, setRows] = useState<Record<string, NominaRow>>({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const [error, setError] = useState("")

  const loadEmpleados = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const all: Empleado[] = []
      let page = 1
      let totalPages = 1
      do {
        const result = await fetchEmpleados({ page, pageSize: 100, estado: "activo" })
        all.push(...result.items)
        totalPages = result.total_pages
        page++
      } while (page <= totalPages)

      setEmpleados(all)
      const initial: Record<string, NominaRow> = {}
      for (const emp of all) initial[emp.id] = { bruto: "", neto: "" }
      setRows(initial)
    } catch {
      setError("No se pudo cargar la lista de colaboradores.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) {
      const d = new Date()
      setMes(d.getMonth() + 1)
      setAnio(d.getFullYear())
      loadEmpleados()
    }
  }, [open, loadEmpleados])

  function updateRow(id: string, field: "bruto" | "neto", value: string) {
    setRows((prev) => ({ ...prev, [id]: { ...prev[id], [field]: value } }))
  }

  async function handleSave() {
    const toSave = empleados.filter((emp) => {
      const row = rows[emp.id]
      return row?.bruto !== "" && row?.neto !== ""
    })

    if (toSave.length === 0) {
      setError("Ingresá al menos un colaborador con monto bruto y monto neto.")
      return
    }

    for (const emp of toSave) {
      const row = rows[emp.id]
      if (isNaN(parseFloat(row.bruto)) || parseFloat(row.bruto) < 0) {
        setError(`Monto bruto inválido para ${emp.nombre} ${emp.apellido}.`)
        return
      }
      if (isNaN(parseFloat(row.neto)) || parseFloat(row.neto) < 0) {
        setError(`Monto neto inválido para ${emp.nombre} ${emp.apellido}.`)
        return
      }
    }

    setSaving(true)
    setProgress({ current: 0, total: toSave.length })
    setError("")

    const failed: string[] = []
    for (let i = 0; i < toSave.length; i++) {
      const emp = toSave[i]
      setProgress({ current: i + 1, total: toSave.length })
      try {
        await cargarNomina({
          empleado_id: emp.id,
          mes,
          anio,
          monto_bruto: parseFloat(rows[emp.id].bruto),
          monto_neto: parseFloat(rows[emp.id].neto),
        })
      } catch {
        failed.push(`${emp.nombre} ${emp.apellido}`)
      }
    }

    setSaving(false)

    if (failed.length > 0) {
      setError(`Error al guardar: ${failed.join(", ")}`)
    } else {
      onSuccess()
    }
  }

  function handleClose() {
    if (!saving) onClose()
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) handleClose() }}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Cargar nómina</DialogTitle>
          <div className="flex items-center gap-2 pt-1">
            <Select
              className="w-auto"
              value={mes}
              onChange={(e) => setMes(Number(e.target.value))}
              disabled={saving}
              aria-label="Mes"
            >
              {MESES_LARGOS.map((label, i) => (
                <option key={i + 1} value={i + 1}>{label}</option>
              ))}
            </Select>
            <Select
              className="w-auto"
              value={anio}
              onChange={(e) => setAnio(Number(e.target.value))}
              disabled={saving}
              aria-label="Año"
            >
              {ANIOS.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </Select>
          </div>
        </DialogHeader>

        {loading && (
          <div className="space-y-2 py-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full rounded" />
            ))}
          </div>
        )}

        {!loading && empleados.length === 0 && !error && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No hay colaboradores activos.
          </p>
        )}

        {!loading && empleados.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="pb-2 pr-4 text-left font-medium text-muted-foreground">Colaborador</th>
                  {!empresaActivaId && (
                    <th className="pb-2 pr-4 text-left font-medium text-muted-foreground">Empresa</th>
                  )}
                  <th className="pb-2 pr-4 text-left font-medium text-muted-foreground">Área</th>
                  <th className="pb-2 pr-4 text-left font-medium text-muted-foreground">Bruto ($)</th>
                  <th className="pb-2 text-left font-medium text-muted-foreground">Neto ($)</th>
                </tr>
              </thead>
              <tbody>
                {empleados.map((emp) => (
                  <tr key={emp.id} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium">
                      {emp.nombre} {emp.apellido}
                    </td>
                    {!empresaActivaId && (
                      <td className="py-2 pr-4 text-muted-foreground">
                        {emp.empresa_nombre ?? "—"}
                      </td>
                    )}
                    <td className="py-2 pr-4 text-muted-foreground">
                      {emp.area_nombre ?? "—"}
                    </td>
                    <td className="py-2 pr-4">
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="0"
                        className="h-8 w-36"
                        value={rows[emp.id]?.bruto ?? ""}
                        onChange={(e) => updateRow(emp.id, "bruto", e.target.value)}
                        disabled={saving}
                        aria-label={`Bruto ${emp.nombre} ${emp.apellido}`}
                      />
                    </td>
                    <td className="py-2">
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="0"
                        className="h-8 w-36"
                        value={rows[emp.id]?.neto ?? ""}
                        onChange={(e) => updateRow(emp.id, "neto", e.target.value)}
                        disabled={saving}
                        aria-label={`Neto ${emp.nombre} ${emp.apellido}`}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {error && (
          <p className="text-sm text-destructive" role="alert">{error}</p>
        )}

        <DialogFooter>
          {saving && (
            <span className="mr-auto flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Guardando {progress.current} de {progress.total}...
            </span>
          )}
          <Button
            type="button"
            variant="outline"
            className="min-h-11"
            onClick={handleClose}
            disabled={saving}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            className="min-h-11"
            onClick={handleSave}
            disabled={loading || saving}
          >
            {saving ? "Guardando..." : "Guardar nómina"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
