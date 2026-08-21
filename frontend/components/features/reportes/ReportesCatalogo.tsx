"use client"

import { GrillaTarjetas } from "@/components/ui/GrillaTarjetas"

import { REPORTES_ESTANDAR } from "./catalogo"
import { ReporteCard } from "./ReporteCard"
import { useReportesFormData } from "./useReportesFormData"

export function ReportesCatalogo({
  canWrite,
  onGenerado,
}: {
  canWrite: boolean
  onGenerado: () => void
}) {
  const { empresas, areas } = useReportesFormData()
  return (
    <section aria-label="Reportes disponibles">
      <h2 className="mb-4 text-base font-semibold text-foreground">Reportes disponibles</h2>
      <GrillaTarjetas>
        {REPORTES_ESTANDAR.map((r) => (
          <ReporteCard
            key={r.id}
            reporte={r}
            canWrite={canWrite}
            empresas={empresas}
            areas={areas}
            onSuccess={onGenerado}
          />
        ))}
      </GrillaTarjetas>
    </section>
  )
}
