"use client"

import { useState } from "react"

import { EmptyState } from "@/components/ui/EmptyState"
import { Select } from "@/components/ui/select"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"
import { PageHeader } from "@/components/layout/PageHeader"
import { HistorialImportaciones } from "@/components/features/evaluaciones/HistorialImportaciones"
import { ImportarEvaluacionesPanel } from "@/components/features/evaluaciones/importar/ImportarEvaluacionesPanel"
import { MetricasPanel } from "@/components/features/evaluaciones/reportes/MetricasPanel"
import { EvaluadosResultadosPanel } from "@/components/features/evaluaciones/resultados/EvaluadosResultadosPanel"
import { useCanWrite } from "@/hooks/useCanWrite"
import { useLotesEvaluaciones } from "@/hooks/useLotesEvaluaciones"
import { ClipboardList } from "lucide-react"

type Tab = "metricas" | "evaluados" | "importar" | "importaciones"

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
  const vacio = (
    <EmptyState
      icon={<ClipboardList />}
      title="Todavía no hay resultados importados"
      description={canWrite ? "Importá los archivos de un ciclo desde la pestaña “Importar resultados”." : "Cuando RRHH cargue un ciclo, vas a ver acá las métricas."}
    />
  )

  return (
    <div>
      <PageHeader title="Evaluaciones de desempeño" description="Resultados importados y métricas del ciclo" />

      {lotes.length > 1 && (tab === "metricas" || tab === "evaluados") && (
        <label className="mb-4 flex flex-col gap-1 text-xs text-muted-foreground">
          Ciclo
          <Select size="sm" className="w-auto" value={loteId ?? ""} onChange={(e) => setLoteId(e.target.value)}>
            {lotes.map((l) => <option key={l.id} value={l.id}>{l.periodo}</option>)}
          </Select>
        </label>
      )}

      <Tabs value={tab} onValueChange={setTab}>
        <TabList className="mb-6">
          {tabs.map((t) => (
            <Tab key={t.id} value={t.id}>{t.label}</Tab>
          ))}
        </TabList>

        {/* Las dos solapas de escritura siguen gateadas por `canWrite`: la solapa ni aparece en
            `tabs`, y el panel tampoco renderiza. Las dos comprobaciones se conservan tal cual. */}
        <TabPanel value="importar">{canWrite && <ImportarEvaluacionesPanel />}</TabPanel>
        <TabPanel value="importaciones">{canWrite && <HistorialImportaciones />}</TabPanel>

        {/* `vacio` se comparte entre las dos solapas de lectura, como antes lo compartía una
            sola condición: duplicar el EmptyState acá lo dejaría divergir. */}
        <TabPanel value="metricas">
          {sinCiclos ? vacio : loteId && <MetricasPanel loteId={loteId} />}
        </TabPanel>
        <TabPanel value="evaluados">
          {sinCiclos ? vacio : loteId && <EvaluadosResultadosPanel loteId={loteId} />}
        </TabPanel>
      </Tabs>
    </div>
  )
}
