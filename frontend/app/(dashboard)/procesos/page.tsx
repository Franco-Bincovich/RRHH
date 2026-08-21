"use client"

import { useCallback, useEffect, useState } from "react"
import { Activity } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { GrillaTarjetas } from "@/components/ui/GrillaTarjetas"
import { Skeleton } from "@/components/ui/skeleton"
import { fetchProcesos } from "@/services/procesos"
import { ProcesoCard } from "@/components/features/procesos/ProcesoCard"
import type { ProcesosData } from "@/services/procesos"

/**
 * El esqueleto son TARJETAS del mismo alto que las reales, con el shimmer de 1,2s que pide §3 —
 * no el `animate-pulse` de 2s: así la pantalla no cambia de forma cuando llegan los datos.
 */
function ProcesosSkeletonGrid() {
  return (
    <GrillaTarjetas>
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} shimmer className="h-44 rounded-xl" />
      ))}
    </GrillaTarjetas>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ProcesosPage() {
  const [data, setData] = useState<ProcesosData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // El reintento del `ErrorState` necesita poder volver a disparar la carga, así que la función
  // sale del efecto y vive acá.
  const cargar = useCallback(() => {
    setLoading(true); setError(null)
    fetchProcesos()
      .then(setData)
      .catch(() => setError("No se pudo cargar el panel de procesos."))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { cargar() }, [cargar])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Panel de Procesos"
        description="Estado actual de los procesos operativos de Capital Humano"
      />

      {loading ? (
        <ProcesosSkeletonGrid />
      ) : error ? (
        <ErrorState description={error} action={cargar} />
      ) : !data || data.procesos.length === 0 ? (
        /*
         * ═══════════════════════════════════════════════════════════════════════════════════
         * 🔴 COPY PROPIO, y no `textoVacio`: acá "vacío" no significa "falta cargar algo".
         * ═══════════════════════════════════════════════════════════════════════════════════
         * Este panel no tiene datos propios: **cuenta lo que hay en los otros módulos**. Un cero
         * acá no es un dato faltante que alguien tenga que ir a cargar —nadie carga "un proceso"—,
         * es que hoy no hay ningún onboarding, offboarding, búsqueda ni objetivo abierto. Decir
         * "cuando se cargue el primero va a aparecer acá" mandaría a buscar una pantalla de alta
         * que no existe.
         */
        <EmptyState
          icon={<Activity />}
          title="No hay ningún proceso abierto"
          description="Este panel cuenta lo que está en curso en los otros módulos: onboarding, offboarding, búsquedas y objetivos. Cuando se abra alguno, aparece acá."
        />
      ) : (
        <GrillaTarjetas>
          {data.procesos.map((p) => (
            <ProcesoCard key={p.proceso} proceso={p} />
          ))}
        </GrillaTarjetas>
      )}
    </div>
  )
}
