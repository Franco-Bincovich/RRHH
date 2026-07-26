"use client"

import { useState } from "react"

import { cn } from "@/lib/utils"
import { EmptyState } from "@/components/ui/EmptyState"
import { PageHeader } from "@/components/layout/PageHeader"
import { HistorialImportaciones } from "@/components/features/evaluaciones/HistorialImportaciones"
import { ImportarEvaluacionesPanel } from "@/components/features/evaluaciones/importar/ImportarEvaluacionesPanel"
import { MetricasPanel } from "@/components/features/evaluaciones/reportes/MetricasPanel"
import { EvaluadosResultadosPanel } from "@/components/features/evaluaciones/resultados/EvaluadosResultadosPanel"
import { useCanWrite } from "@/hooks/useCanWrite"
import { useLotesEvaluaciones } from "@/hooks/useLotesEvaluaciones"
import { ClipboardList } from "lucide-react"

type Tab = "metricas" | "evaluados" | "importar" | "importaciones"

const SELECT_CLASS =
  "min-h-9 rounded-lg border border-input bg-transparent px-3 py-1.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"

export default function EvaluacionesPage() {
  const canWrite = useCanWrite() // write en evaluaciones = admin_rrhh
  const { lotes, loteId, setLoteId, cargando } = useLotesEvaluaciones()
  const [tab, setTab] = useState<Tab>("metricas")

  const tabs: { id: Tab; label: string }[] = [
    { id: "metricas", label: "Métricas" },
    { id: "evaluados", label: "Evaluados" },
    ...(canWrite ? [
      { id: "importar" as Tab, label: "Importar resultados" },
      { id: "importaciones" as Tab, label: "Importaciones" },
    ] : []),
  ]
  const sinCiclos = !cargando && !loteId

  return (
    <div>
      <PageHeader title="Evaluaciones de desempeño" description="Resultados importados y métricas del ciclo" />

      {lotes.length > 1 && (tab === "metricas" || tab === "evaluados") && (
        <label className="mb-4 flex flex-col gap-1 text-xs text-muted-foreground">
          Ciclo
          <select className={SELECT_CLASS} value={loteId ?? ""} onChange={(e) => setLoteId(e.target.value)}>
            {lotes.map((l) => <option key={l.id} value={l.id}>{l.periodo}</option>)}
          </select>
        </label>
      )}

      <div className="mb-6 flex gap-1 border-b border-border">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "px-4 pb-3 pt-1 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              tab === t.id ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "importar" && canWrite && <ImportarEvaluacionesPanel />}
      {tab === "importaciones" && canWrite && <HistorialImportaciones />}
      {(tab === "metricas" || tab === "evaluados") && sinCiclos && (
        <EmptyState
          icon={<ClipboardList />}
          title="Todavía no hay resultados importados"
          description={canWrite ? "Importá los archivos de un ciclo desde la pestaña “Importar resultados”." : "Cuando RRHH cargue un ciclo, vas a ver acá las métricas."}
        />
      )}
      {tab === "metricas" && loteId && <MetricasPanel loteId={loteId} />}
      {tab === "evaluados" && loteId && <EvaluadosResultadosPanel loteId={loteId} />}
    </div>
  )
}
