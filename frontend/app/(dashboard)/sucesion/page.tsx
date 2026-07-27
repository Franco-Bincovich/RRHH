"use client"

import { useState } from "react"
import { Tabs } from "@base-ui/react/tabs"

import { PageHeader } from "@/components/layout/PageHeader"
import { AnalisisAreaModal } from "@/components/features/sucesion/AnalisisAreaModal"
import { MapaTalentoTab } from "@/components/features/sucesion/MapaTalentoTab"
import { NuevoPlanModal } from "@/components/features/sucesion/NuevoPlanModal"
import { PlanDetallePanel } from "@/components/features/sucesion/PlanDetallePanel"
import { PlanesTab } from "@/components/features/sucesion/PlanesTab"
import { TAB_CLASS } from "@/components/features/sucesion/_sucesion_ui"
import { usePlanDetalle } from "@/components/features/sucesion/usePlanDetalle"
import { useSucesionData } from "@/components/features/sucesion/useSucesionData"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"

export default function SucesionPage() {
  const canWrite = useCanWrite()
  const [empresaActivaId] = useState<string | null>(() => getEmpresaActivaId())
  const [planOpen, setPlanOpen] = useState(false)
  const [analisisOpen, setAnalisisOpen] = useState(false)

  const datos = useSucesionData()
  const detalle = usePlanDetalle(datos.setPlanes)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sucesión y Planes de Carrera"
        description="Mapa de talento y trayectorias de desarrollo"
      />

      <Tabs.Root defaultValue="mapa" className="space-y-6">
        <Tabs.List className="inline-flex gap-0.5 rounded-xl bg-muted p-1">
          <Tabs.Tab value="mapa" className={TAB_CLASS}>Mapa de Talento</Tabs.Tab>
          <Tabs.Tab value="planes" className={TAB_CLASS}>Planes de Carrera</Tabs.Tab>
        </Tabs.List>

        {/* ── Tab 1: 9-Box ──────────────────────────────────────────────── */}
        <Tabs.Panel value="mapa" className="space-y-4">
          <MapaTalentoTab
            empleados={datos.rawEmpleados}
            areas={datos.areas}
            selectedArea={datos.selectedArea}
            onSelectArea={datos.setSelectedArea}
            loading={datos.loadingMapa}
            error={datos.errorMapa}
            onAnalizar={() => setAnalisisOpen(true)}
          />
        </Tabs.Panel>

        {/* ── Tab 2: Planes de carrera ───────────────────────────────────── */}
        <Tabs.Panel value="planes">
          <PlanesTab
            planes={datos.planes}
            loading={datos.loadingPlanes}
            error={datos.errorPlanes}
            mostrarEmpresa={!empresaActivaId}
            canWrite={canWrite}
            onNuevoPlan={() => setPlanOpen(true)}
            onVerDetalle={detalle.abrir}
          />
        </Tabs.Panel>
      </Tabs.Root>

      {detalle.selectedPlan && (
        <PlanDetallePanel plan={detalle.selectedPlan} detalle={detalle} canWrite={canWrite} />
      )}

      <NuevoPlanModal
        open={planOpen}
        onOpenChange={setPlanOpen}
        onCreado={datos.recargarPlanes}
      />

      <AnalisisAreaModal
        open={analisisOpen}
        onOpenChange={setAnalisisOpen}
        areas={datos.areas}
        areaInicial={datos.selectedArea}
      />
    </div>
  )
}
