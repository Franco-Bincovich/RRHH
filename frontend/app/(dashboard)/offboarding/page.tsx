"use client"

import { useState } from "react"
import { UserMinus } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { AdjuntosDialog } from "@/components/features/adjuntos/AdjuntosDialog"
import { OffboardingCard } from "@/components/features/offboarding/OffboardingCard"
import { useOffboardings } from "@/components/features/offboarding/useOffboardings"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarOffboardings } from "@/services/offboarding"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { OffboardingInstancia } from "@/types/offboarding"

/**
 * Listado de procesos de offboarding abiertos.
 *
 * Quedó como orquestador tras el corte del 19/8/2026 (311 → esto), que hizo falta para poder
 * sumarle la efectivización de la baja: el estado y el update optimista se fueron a
 * `useOffboardings`, la tarjeta a `OffboardingCard` y los mapas de texto a `_offboardingLabels`.
 */
export default function OffboardingPage() {
  const canWrite = useCanWrite()
  const { offboardings, loading, error, saving, toggleActivo, marcarEntrevista, quitar } =
    useOffboardings()
  const [empresaActivaId] = useState<string | null>(() => getEmpresaActivaId())
  const [docsFor, setDocsFor] = useState<OffboardingInstancia | null>(null)

  // mostrar empresa solo cuando el topbar está en "Todas"
  const mostrarEmpresa = !empresaActivaId

  if (loading) {
    return (
      <div>
        <PageHeader title="Offboarding" description="Cargando..." />
        <ul className="space-y-4" role="list">
          {[1, 2].map((i) => (
            <li key={i} className="h-40 animate-pulse rounded-xl bg-muted" />
          ))}
        </ul>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Offboarding" description="Error al cargar" />
        <p className="text-sm text-destructive">{error}</p>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Offboarding"
        description={`${offboardings.length} procesos activos`}
        // El archivo sale del MISMO listado que las tarjetas y esta pantalla no tiene filtros:
        // trae exactamente los procesos que se ven. Sin procesos no se ofrece exportar.
        action={offboardings.length > 0 ? <ExportMenu onExport={exportarOffboardings} /> : undefined}
      />

      {offboardings.length === 0 ? (
        <EmptyState
          icon={<UserMinus />}
          title="Sin procesos activos"
          description="No hay empleados en proceso de offboarding actualmente."
        />
      ) : (
        <ul className="space-y-4" role="list">
          {offboardings.map((inst) => (
            <OffboardingCard
              key={inst.id}
              instancia={inst}
              canWrite={canWrite}
              mostrarEmpresa={mostrarEmpresa}
              saving={saving}
              onToggleActivo={toggleActivo}
              onDocumentos={setDocsFor}
              onEntrevista={marcarEntrevista}
              onEfectivizada={quitar}
            />
          ))}
        </ul>
      )}

      <AdjuntosDialog
        open={!!docsFor}
        onClose={() => setDocsFor(null)}
        entidad="offboarding"
        entidadId={docsFor?.id ?? ""}
        titulo={`Offboarding · ${docsFor?.empleado_nombre ?? ""}`}
      />
    </div>
  )
}
