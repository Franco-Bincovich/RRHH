"use client"

import { useState } from "react"

import { EmptyState } from "@/components/ui/EmptyState"
import { Button } from "@/components/ui/button"
import { Select } from "@/components/ui/select"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"
import { PageHeader } from "@/components/layout/PageHeader"
import { HistorialImportaciones } from "@/components/features/evaluaciones/HistorialImportaciones"
import { ImportarEvaluacionesPanel } from "@/components/features/evaluaciones/importar/ImportarEvaluacionesPanel"
import { MetricasPanel } from "@/components/features/evaluaciones/reportes/MetricasPanel"
import { EvaluadosResultadosPanel } from "@/components/features/evaluaciones/resultados/EvaluadosResultadosPanel"
import { useCanWrite } from "@/hooks/useCanWrite"
import { useLotesEvaluaciones } from "@/hooks/useLotesEvaluaciones"
import { ClipboardList, Upload } from "lucide-react"

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
  // 🔴 SE LLAMA `sinResultados` Y NO `sinCiclos`: la variable nombraba el concepto que este
  // módulo justamente NO tiene. Ver el 🔴 del selector de abajo.
  const sinResultados = !cargando && !loteId
  /**
   * 🔴 EL VACÍO LLEVA A LA ACCIÓN, NO SÓLO LA NOMBRA (25/8/2026). La descripción decía *"Importá
   * los dos archivos desde la pestaña «Importar resultados»"* y no ofrecía nada: mandaba a buscar
   * una pestaña estando el `setTab` a tres líneas de distancia. Es el mismo defecto que en
   * /proximos-ingresos, donde el error decía "corregí la fecha en el legajo" desde una pantalla
   * que no tenía cómo abrirlo.
   *
   * Sin permiso de escritura NO se ofrece —importar es una escritura— y ahí el texto es el otro:
   * dice qué va a pasar cuando alguien lo haga, que es lo único accionable para ese rol.
   */
  const vacio = (
    <EmptyState
      icon={<ClipboardList />}
      title="Todavía no hay resultados importados"
      description={canWrite
        ? "Los resultados se calculan afuera y se importan: hacen falta los dos archivos del período."
        : "Cuando Capital Humano importe los resultados de un período, vas a ver acá las métricas."}
      action={canWrite ? (
        <Button className="min-h-11" onClick={() => setTab("importar")}>
          <Upload />
          Importar resultados
        </Button>
      ) : undefined}
    />
  )

  return (
    <div>
      {/* El subtítulo dice lo que la pantalla ES: resultados que se importan, no evaluaciones
          que el sistema corra. Decía "métricas del ciclo". */}
      <PageHeader
        title="Evaluaciones de desempeño"
        description="Resultados calculados afuera e importados por período — el sistema no corre las evaluaciones"
      />

      {/*
       * 🔴 DICE "PERÍODO IMPORTADO" Y NO "CICLO", y no es una preferencia de estilo.
       * El sistema **no corre evaluaciones: IMPORTA resultados** calculados afuera
       * (`docs/SISTEMA-DE-DISENO.md` §7). "Ciclo" nombra un proceso que la herramienta abriría,
       * seguiría y cerraría —con instancias, vencimientos y recordatorios— y **nada de eso
       * existe**: no hay evaluaciones pendientes ni vencidas que mostrar. Lo que hay es un LOTE
       * de importación identificado por su período, y este selector elige cuál mirar.
       *
       * ⚠️ Y NO ES UN FILTRO DEL PANEL DE CHIPS: elegir el lote no recorta un listado, decide
       * QUÉ listado se pide (`loteId` va en la ruta). Un chip prometería que se puede quitar, y
       * sin lote no hay nada que mostrar. Mismo criterio que el período obligatorio de /costos.
       */}
      {lotes.length > 1 && (tab === "metricas" || tab === "evaluados") && (
        <label className="mb-4 flex flex-col gap-1 text-xs text-muted-foreground">
          Período importado
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
          {sinResultados ? vacio : loteId && <MetricasPanel loteId={loteId} />}
        </TabPanel>
        <TabPanel value="evaluados">
          {sinResultados ? vacio : loteId && <EvaluadosResultadosPanel loteId={loteId} />}
        </TabPanel>
      </Tabs>
    </div>
  )
}
