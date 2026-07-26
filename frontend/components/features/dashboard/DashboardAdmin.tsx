"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { AlertTriangle } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Badge } from "@/components/ui/badge"
import { fetchDashboard } from "@/services/dashboard"
import type { DashboardData, HeadcountArea } from "@/services/dashboard"
import { buildKpis, NIVEL_LABEL, NIVEL_VARIANT, type KpiCardData } from "./dashboardAdminData"
import { DashboardExtras } from "./DashboardExtras"

function KpiCard({ kpi }: { kpi: KpiCardData }) {
  const Icon = kpi.icon
  return (
    <div className="rounded-xl border bg-card p-4 md:p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-muted-foreground">{kpi.title}</p>
        <span className="shrink-0 rounded-lg bg-primary/10 p-1.5 text-primary">
          <Icon className="size-4" />
        </span>
      </div>
      <p className="mt-3 text-2xl font-bold tracking-tight text-foreground">{kpi.value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{kpi.description}</p>
    </div>
  )
}

function HeadcountBar({ area, total, max }: HeadcountArea & { max: number }) {
  const pct = max > 0 ? Math.round((total / max) * 100) : 0
  return (
    // Layout apilado: el nombre ocupa todo el ancho (trunca con tooltip si es muy largo),
    // el número queda arriba a la derecha y la barra va full-width debajo, siempre alineados.
    <div className="space-y-1.5">
      <div className="flex items-baseline gap-3">
        <span className="min-w-0 flex-1 truncate text-sm text-muted-foreground" title={area}>{area}</span>
        <span className="shrink-0 text-sm font-medium text-foreground">{total}</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function KpiSkeleton() {
  return (
    <div className="grid animate-pulse grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3, 4, 5, 6].map((i) => <div key={i} className="h-28 rounded-xl border bg-muted" />)}
    </div>
  )
}

export function DashboardAdmin() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch(() => setError("No se pudo cargar el dashboard."))
      .finally(() => setLoading(false))
  }, [])

  const kpis = data ? buildKpis(data) : []
  const maxHeadcount = data ? Math.max(...data.headcount_por_area.map((h) => h.total), 1) : 1

  return (
    <div className="space-y-6">
      <PageHeader title="Dashboard Ejecutivo" description="Resumen del estado de la organización" />

      {/* KPIs — 1 col mobile / 2 col tablet / 3 col desktop */}
      <section aria-label="Indicadores clave">
        {loading ? (
          <KpiSkeleton />
        ) : error ? (
          <p className="py-8 text-center text-sm text-destructive">{error}</p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {kpis.map((kpi) => <KpiCard key={kpi.title} kpi={kpi} />)}
          </div>
        )}
      </section>

      {/* Headcount + Alertas */}
      {data && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section className="rounded-xl border bg-card p-4 md:p-6" aria-label="Headcount por área">
            <h2 className="mb-5 text-base font-semibold text-foreground">Headcount por área</h2>
            {data.headcount_por_area.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin datos de headcount.</p>
            ) : (
              <div className="space-y-4">
                {data.headcount_por_area.map((row) => (
                  <HeadcountBar key={row.area_id} {...row} max={maxHeadcount} />
                ))}
              </div>
            )}
          </section>

          <section className="rounded-xl border bg-card p-4 md:p-6" aria-label="Alertas activas">
            <h2 className="mb-4 text-base font-semibold text-foreground">Alertas activas</h2>
            {data.alertas.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin alertas activas.</p>
            ) : (
              <ul className="divide-y divide-border" role="list">
                {data.alertas.map((alerta, i) => (
                  <li key={i} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
                    <AlertTriangle className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                    {alerta.entidad_id ? (
                      <Link
                        href={`/empleados/${alerta.entidad_id}`}
                        className="min-w-0 flex-1 text-sm text-foreground hover:underline"
                      >
                        {alerta.mensaje}
                      </Link>
                    ) : (
                      <p className="min-w-0 flex-1 text-sm text-foreground">{alerta.mensaje}</p>
                    )}
                    <Badge variant={NIVEL_VARIANT[alerta.nivel]} className="shrink-0">{NIVEL_LABEL[alerta.nivel]}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}

      {/* KPIs Sesión 5 — distribución + cumpleaños/aniversarios */}
      {data && <DashboardExtras data={data.kpis_extra} />}
    </div>
  )
}
