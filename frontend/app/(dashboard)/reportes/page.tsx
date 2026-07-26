"use client"

import { useState } from "react"

import { PageHeader } from "@/components/layout/PageHeader"
import { HistorialReportesTable } from "@/components/features/reportes/HistorialReportesTable"
import { ReportesCatalogo } from "@/components/features/reportes/ReportesCatalogo"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import { useReportes } from "@/hooks/useReportes"

export default function ReportesPage() {
  const canWrite = useCanWrite()
  const [empresaActivaId] = useState<string | null>(() => getEmpresaActivaId())
  const { historial, historialLoading, exportLoading, cargarHistorial, exportar } = useReportes()

  return (
    <div className="space-y-8">
      <PageHeader
        title="Reportes y Exportaciones"
        description="Generá reportes estándar descargables en PDF o Excel"
      />

      <ReportesCatalogo canWrite={canWrite} onGenerado={cargarHistorial} />

      <HistorialReportesTable
        historial={historial}
        loading={historialLoading}
        mostrarEmpresa={!empresaActivaId}
        exportLoading={exportLoading}
        onExportar={exportar}
      />
    </div>
  )
}
