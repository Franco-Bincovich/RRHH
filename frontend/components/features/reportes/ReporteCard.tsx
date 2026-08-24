"use client"

import { useState } from "react"
import { type LucideIcon } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { generarYDescargar, type TipoReporte, type VistaAusentismo } from "@/services/reportes"
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
  const [bajando, setBajando] = useState<"pdf" | "excel" | null>(null)

  function handleEmpresaChange(v: string) {
    setEmpresaId(v)
    setAreaId("") // el área depende de la empresa: al cambiarla, se resetea
  }

  async function handleDescargar(formato: "pdf" | "excel") {
    setBajando(formato)
    try {
      await generarYDescargar({
        tipo: reporte.id,
        ...(reporte.usaPeriodo ? { mes, anio } : {}),
        ...(reporte.usaAnio ? { anio } : {}),
        // Empresa/área del FORM (no del sidebar); omitidas = consolidado / todas las áreas.
        ...(empresaId ? { empresa_id: empresaId } : {}),
        ...(usaArea && areaId ? { area_id: areaId } : {}),
        ...(reporte.usaVista ? { vista } : {}),
      }, formato)
      toast.success(`${reporte.titulo}: ${formato.toUpperCase()} descargado`)
      onSuccess()   // el reporte queda además en el historial, para volver a bajarlo
    } catch {
      toast.error("No se pudo generar el reporte. Intentá de nuevo.")
    } finally {
      setBajando(null)
    }
  }

  // ⚠️ SIN HOVER DE TARJETA (§2), y no es un olvido: la tarjeta no es un control, es un
  // FORMULARIO. Adentro hay tres selectores y un botón, y cada uno se apunta por separado;
  // levantar la superficie entera mientras el usuario elige un mes movería justo lo que está
  // por apretar. El control es "Generar".
  return (
    <Card padding="sm" interactive className="flex flex-col gap-4">
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

      {/* 🔴 DOS BOTONES Y NO UNO, Y CADA UNO BAJA EL ARCHIVO. El botón anterior decía
          "Generar", dejaba una fila en el historial de abajo y no descargaba nada: el usuario
          leía "generado exitosamente" y se quedaba sin el archivo que la pantalla promete.
          El formato es parte de la acción, no un paso posterior. */}
      {canWrite && (
        <div className="mt-auto flex gap-2">
          {(["pdf", "excel"] as const).map((f) => (
            <Button
              key={f}
              variant="outline"
              size="sm"
              className="min-h-[2.75rem] flex-1"
              onClick={() => handleDescargar(f)}
              disabled={bajando !== null}
            >
              {bajando === f ? "Generando…" : f === "pdf" ? "PDF" : "Excel"}
            </Button>
          ))}
        </div>
      )}
    </Card>
  )
}
