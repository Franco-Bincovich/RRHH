"use client"

import { useState, useEffect, useCallback } from "react"
import { DollarSign, FileSpreadsheet, Upload } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Button } from "@/components/ui/button"
import { NominaModal } from "@/components/features/costos/NominaModal"
import { ImportarNominaCSVModal } from "@/components/features/costos/ImportarNominaCSVModal"
import { CostosPorAreaTable } from "@/components/features/costos/CostosPorAreaTable"
import { DashboardSkeleton, EvolucionChart } from "@/components/features/costos/EvolucionChart"
import { KpisCostos } from "@/components/features/costos/KpisCostos"
import { NominaSection } from "@/components/features/costos/NominaSection"
import { PeriodSelector } from "@/components/features/costos/PeriodSelector"
import { MESES_LARGOS, totalesDeAreas } from "@/components/features/costos/formatos"
import { fetchDashboardCostos } from "@/services/costos"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { DashboardCostos } from "@/types/costo"

/**
 * Costos de Personal — ORQUESTADOR.
 *
 * Estaba en 624 líneas contra un límite de 150. El corte se hizo ANTES de paginar el detalle de
 * nómina, y con eso a la vista: cada pieza se llevó lo suyo a `components/features/costos/`.
 *
 * 🔑 POR DÓNDE PASA EL CORTE, que no es arbitrario: separa **lo que agrega el backend** de **lo
 * que pagina**. `KpisCostos` y `CostosPorAreaTable` leen `dashboard`, que viene ya agregado de
 * `/api/costos/dashboard` y trae una fila por área — sumarlo es correcto. `NominaSection` lee el
 * detalle, que es una lista PAGINADA y de la que no puede salir ningún total. Tenerlos en el
 * mismo archivo era lo que hacía fácil confundirse y calcular un KPI con la página.
 *
 * Los dos fetch quedan separados a propósito: el dashboard y el detalle son consultas distintas
 * y `NominaSection` avisa por `onGuardado` cuando editar un sueldo obliga a recargar los KPIs.
 */
export default function CostosPage() {
  const canWrite = useCanWrite()
  const now = new Date()
  // empresa activa del topbar — estable (el topbar recarga la página al cambiar)
  const [empresaActivaId] = useState<string | null>(() =>
    typeof window !== "undefined" ? getEmpresaActivaId() : null
  )
  const [mes, setMes] = useState(now.getMonth() + 1)
  const [anio, setAnio] = useState(now.getFullYear())
  const [dashboard, setDashboard] = useState<DashboardCostos | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [nominaOpen, setNominaOpen] = useState(false)
  const [importarNominaOpen, setImportarNominaOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      setDashboard(await fetchDashboardCostos(mes, anio))
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [mes, anio])

  useEffect(() => { load() }, [load])

  const isEmpty =
    !loading && !error && dashboard !== null && dashboard.costos_por_area.length === 0
  const { totalEmpleados } = totalesDeAreas(dashboard)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Costos de Personal"
        description={`Nómina y presupuesto — ${MESES_LARGOS[mes - 1]} ${anio}`}
        action={
          <div className="flex items-center gap-2">
            <PeriodSelector mes={mes} anio={anio} onChangeMes={setMes} onChangeAnio={setAnio} />
            {canWrite && (
              <>
                <Button variant="outline" className="min-h-11 gap-1.5" onClick={() => setImportarNominaOpen(true)}>
                  <FileSpreadsheet className="size-4" />
                  Importar CSV
                </Button>
                <Button className="min-h-11 gap-1.5" onClick={() => setNominaOpen(true)}>
                  <Upload className="size-4" />
                  Cargar nómina
                </Button>
              </>
            )}
          </div>
        }
      />

      {loading && <DashboardSkeleton />}

      {error && (
        <ErrorState description="No se pudo cargar el dashboard de costos." action={load} />
      )}

      {isEmpty && (
        <EmptyState
          icon={<DollarSign />}
          title="Sin datos de nómina"
          description={`No hay registros de nómina para ${MESES_LARGOS[mes - 1]} ${anio}. Cargá la nómina del período para ver los costos.`}
          action={
            canWrite ? (
              <Button type="button" className="mt-1 min-h-11 gap-1.5" onClick={() => setNominaOpen(true)}>
                <Upload className="size-4" />
                Cargar nómina
              </Button>
            ) : undefined
          }
        />
      )}

      {!loading && !error && !isEmpty && dashboard && (
        <>
          <KpisCostos dashboard={dashboard} mes={mes} anio={anio} totalEmpleados={totalEmpleados} />
          <EvolucionChart data={dashboard.evolucion_mensual} />
          <CostosPorAreaTable dashboard={dashboard} mostrarEmpresa={!empresaActivaId} />
        </>
      )}

      {!loading && (
        <NominaSection
          mes={mes} anio={anio} canWrite={canWrite}
          mostrarEmpresa={!empresaActivaId} onGuardado={load}
        />
      )}

      <NominaModal
        open={nominaOpen}
        onClose={() => setNominaOpen(false)}
        onSuccess={() => { setNominaOpen(false); load() }}
      />

      <ImportarNominaCSVModal
        open={importarNominaOpen}
        onClose={() => setImportarNominaOpen(false)}
        onSuccess={() => { setImportarNominaOpen(false); load() }}
      />
    </div>
  )
}
