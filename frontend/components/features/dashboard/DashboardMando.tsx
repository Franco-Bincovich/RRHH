"use client"

import { useCallback, useEffect, useState } from "react"
import { CalendarX2, Umbrella, Users } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { ErrorState } from "@/components/ui/ErrorState"
import { fetchDashboardEquipo } from "@/services/dashboardEquipo"
import type { DashboardEquipo } from "@/types/dashboardEquipo"

interface Widget {
  title: string
  value: number
  icon: LucideIcon
  description: string
}

// Mismo patrón visual que KpiCard del dashboard de admin (rounded-xl border bg-card).
function StatCard({ title, value, icon: Icon, description }: Widget) {
  return (
    <div className="rounded-xl border bg-card p-4 md:p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <span className="shrink-0 rounded-lg bg-primary/10 p-1.5 text-primary">
          <Icon className="size-4" />
        </span>
      </div>
      <p className="mt-3 text-3xl font-bold tracking-tight text-foreground">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{description}</p>
    </div>
  )
}

function CardsSkeleton() {
  return (
    <div className="grid animate-pulse grid-cols-1 gap-4 sm:grid-cols-3">
      {[1, 2, 3].map((i) => <div key={i} className="h-28 rounded-xl border bg-muted" />)}
    </div>
  )
}

export function DashboardMando() {
  const [data, setData] = useState<DashboardEquipo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      setData(await fetchDashboardEquipo())
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Los ceros son datos válidos (mando sin gente), no un empty state — se muestran normales.
  const widgets: Widget[] = data
    ? [
        { title: "Colaboradores a cargo", value: data.empleados_a_cargo, icon: Users, description: "Personas de tu equipo" },
        { title: "De vacaciones este mes", value: data.vacaciones_mes, icon: Umbrella, description: "Solicitudes que tocan el mes en curso" },
        { title: "Ausencias este mes", value: data.ausencias_mes, icon: CalendarX2, description: "Registros que tocan el mes en curso" },
      ]
    : []

  return (
    <div className="space-y-6">
      <PageHeader title="Mi equipo" description="Resumen de tu equipo este mes" />

      <section aria-label="Indicadores de mi equipo">
        {loading ? (
          <CardsSkeleton />
        ) : error ? (
          <ErrorState action={load} />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {widgets.map((w) => <StatCard key={w.title} {...w} />)}
          </div>
        )}
      </section>
    </div>
  )
}
