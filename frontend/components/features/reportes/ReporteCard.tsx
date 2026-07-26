"use client"

import { useState } from "react"
import { type LucideIcon } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { generarReporte, type TipoReporte, type VistaAusentismo } from "@/services/reportes"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"
import { EmpresaAreaSelector } from "./EmpresaAreaSelector"
import { AnioSelector, ANO_ACTUAL, MES_ACTUAL, PeriodoSelector, VistaSelector } from "./PeriodoSelectors"

export interface ReporteEstandar {
  id: TipoReporte
  titulo: string
  descripcion: string
  icon: LucideIcon
  usaPeriodo: boolean
  usaAnio?: boolean
  usaArea?: boolean // false = sin selector de área (ej. anual_consolidado, transversal). Default: true.
  usaVista?: boolean // true = selector de vista total/injustificado/ambos (solo ausentismo)
}

export function ReporteCard({
  reporte,
  canWrite,
  empresas,
  areas,
  onSuccess,
}: {
  reporte: ReporteEstandar
  canWrite: boolean
  empresas: Empresa[]
  areas: Area[]
  onSuccess: () => void
}) {
  const Icon = reporte.icon
  const usaArea = reporte.usaArea !== false
  const [mes, setMes] = useState(MES_ACTUAL)
  const [anio, setAnio] = useState(ANO_ACTUAL)
  const [empresaId, setEmpresaId] = useState("")
  const [areaId, setAreaId] = useState("")
  const [vista, setVista] = useState<VistaAusentismo>("ambos")
  const [loading, setLoading] = useState(false)

  function handleEmpresaChange(v: string) {
    setEmpresaId(v)
    setAreaId("") // el área depende de la empresa: al cambiarla, se resetea
  }

  async function handleGenerar() {
    setLoading(true)
    try {
      await generarReporte({
        tipo: reporte.id,
        ...(reporte.usaPeriodo ? { mes, anio } : {}),
        ...(reporte.usaAnio ? { anio } : {}),
        // Empresa/área del FORM (no del sidebar); omitidas = consolidado / todas las áreas.
        ...(empresaId ? { empresa_id: empresaId } : {}),
        ...(usaArea && areaId ? { area_id: areaId } : {}),
        ...(reporte.usaVista ? { vista } : {}),
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

      <EmpresaAreaSelector
        id={reporte.id}
        empresas={empresas}
        areas={areas}
        empresaId={empresaId}
        areaId={areaId}
        usaArea={usaArea}
        onEmpresaChange={handleEmpresaChange}
        onAreaChange={setAreaId}
      />

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

      {reporte.usaVista && (
        <VistaSelector id={reporte.id} vista={vista} onVistaChange={(v) => setVista(v as VistaAusentismo)} />
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
