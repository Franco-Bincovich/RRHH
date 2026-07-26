"use client"

import { useState } from "react"
import { type LucideIcon } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { generarReporte, type TipoReporte } from "@/services/reportes"
import { AnioSelector, ANO_ACTUAL, MES_ACTUAL, PeriodoSelector } from "./PeriodoSelectors"

export interface ReporteEstandar {
  id: TipoReporte
  titulo: string
  descripcion: string
  icon: LucideIcon
  usaPeriodo: boolean
  usaAnio?: boolean
}

export function ReporteCard({
  reporte,
  canWrite,
  onSuccess,
}: {
  reporte: ReporteEstandar
  canWrite: boolean
  onSuccess: () => void
}) {
  const Icon = reporte.icon
  const [mes, setMes] = useState(MES_ACTUAL)
  const [anio, setAnio] = useState(ANO_ACTUAL)
  const [loading, setLoading] = useState(false)

  async function handleGenerar() {
    setLoading(true)
    try {
      await generarReporte({
        tipo: reporte.id,
        ...(reporte.usaPeriodo ? { mes, anio } : {}),
        ...(reporte.usaAnio ? { anio } : {}),
      })
      toast.success(`${reporte.titulo} generado exitosamente`)
      onSuccess()
    } catch {
      toast.error("No se pudo generar el reporte. Intentá de nuevo.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border bg-card p-5">
      <div className="flex items-start gap-3">
        <span className="shrink-0 rounded-lg bg-primary/10 p-2 text-primary">
          <Icon className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-foreground">{reporte.titulo}</h3>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            {reporte.descripcion}
          </p>
        </div>
      </div>

      {reporte.usaPeriodo && (
        <PeriodoSelector
          id={reporte.id}
          mes={mes}
          anio={anio}
          onMesChange={setMes}
          onAnioChange={setAnio}
        />
      )}

      {reporte.usaAnio && (
        <AnioSelector id={reporte.id} anio={anio} onAnioChange={setAnio} />
      )}

      {canWrite && (
        <Button
          variant="outline"
          size="sm"
          className="mt-auto min-h-[2.75rem] w-full"
          onClick={handleGenerar}
          disabled={loading}
        >
          {loading ? "Generando…" : "Generar"}
        </Button>
      )}
    </div>
  )
}
