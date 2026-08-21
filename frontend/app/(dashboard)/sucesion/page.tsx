"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"

import { PageHeader } from "@/components/layout/PageHeader"
import { AnalisisAreaModal } from "@/components/features/sucesion/AnalisisAreaModal"
import { MapaTalentoTab } from "@/components/features/sucesion/MapaTalentoTab"
import { NuevoPlanModal } from "@/components/features/sucesion/NuevoPlanModal"
import { PlanDetallePanel } from "@/components/features/sucesion/PlanDetallePanel"
import { PlanesTab } from "@/components/features/sucesion/PlanesTab"
import { usePlanDetalle } from "@/components/features/sucesion/usePlanDetalle"
import { useSucesionData } from "@/components/features/sucesion/useSucesionData"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"

export default function SucesionPage() {
  const router = useRouter()
  // Módulo desactivado a propósito (no es un bug): redirige a /dashboard y no renderiza.
  // Es useState y NO const a propósito: un const colapsa a literal `false` por control-flow,
  // TS re-marca el cuerpo inalcanzable, se pierde el narrowing y `next build` falla.
  // Para reactivar: useState(true) acá + SUCESION_ACTIVA = true en components/layout/nav-config.ts.
  const [moduloActivo] = useState(false)

  useEffect(() => {
    if (!moduloActivo) router.replace("/dashboard")
  }, [router, moduloActivo])

  if (!moduloActivo) return null

  return <SucesionContenido />
}

// El contenido vive en un componente aparte —y no en el cuerpo de arriba, como en assessment—
// porque acá la carga de datos está en hooks (useSucesionData / usePlanDetalle) y no en un
// useEffect que se pueda gatear. Si estuviera todo junto, los hooks correrían igual y la
// pantalla desactivada dispararía llamadas al backend antes de redirigir. Así no se monta nada.
function SucesionContenido() {
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

      <Tabs variant="pill" defaultValue="mapa" className="space-y-6">
        <TabList>
          <Tab value="mapa">Mapa de Talento</Tab>
          <Tab value="planes">Planes de Carrera</Tab>
        </TabList>

        {/* ── Tab 1: 9-Box ──────────────────────────────────────────────── */}
        <TabPanel value="mapa" className="space-y-4">
          <MapaTalentoTab
            empleados={datos.rawEmpleados}
            areas={datos.areas}
            selectedArea={datos.selectedArea}
            onSelectArea={datos.setSelectedArea}
            loading={datos.loadingMapa}
            error={datos.errorMapa}
            onReintentar={datos.recargarMapa}
            onAnalizar={() => setAnalisisOpen(true)}
          />
        </TabPanel>

        {/* ── Tab 2: Planes de carrera ───────────────────────────────────── */}
        <TabPanel value="planes">
          <PlanesTab
            planes={datos.planes}
            loading={datos.loadingPlanes}
            error={datos.errorPlanes}
            onReintentar={datos.recargarPlanes}
            mostrarEmpresa={!empresaActivaId}
            canWrite={canWrite}
            onNuevoPlan={() => setPlanOpen(true)}
            onVerDetalle={detalle.abrir}
          />
        </TabPanel>
      </Tabs>

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
