"use client"

import { Skeleton } from "@/components/ui/skeleton"
import { MESES_CORTOS } from "@/components/features/costos/formatos"
import type { EvolucionMes } from "@/types/costo"

/**
 * El gráfico de evolución mensual y el esqueleto de carga de la pantalla de Costos.
 *
 * Movidos VERBATIM desde `costos/page.tsx` al partirla. Van juntos porque el esqueleto describe
 * la forma de ESTA pantalla —cuatro tarjetas, gráfico, dos tablas— y cambia con ella.
 *
 * ⚠️ El `.map()` sobre `data` NO es un agregado sobre una lista paginada: `evolucion_mensual` son
 * 12 puntos que el backend ya calculó. El `Math.max` sobre ellos es la escala del gráfico.
 */
export function EvolucionChart({ data }: { data: EvolucionMes[] }) {
  if (!data.length) return null
  const max = Math.max(...data.map((d) => d.total))
  const BAR_MAX_PX = 128

  return (
    <section
      className="rounded-xl border bg-card p-4 md:p-6"
      aria-label="Evolución mensual del costo de nómina"
    >
      <h2 className="mb-5 text-base font-semibold text-foreground">Evolución mensual</h2>
      <div className="flex h-32 gap-3">
        {data.map((d) => {
          const barPx = max > 0 ? Math.round((d.total / max) * BAR_MAX_PX) : 0
          const label =
            d.total >= 1_000_000
              ? `$${(d.total / 1_000_000).toFixed(1)}M`
              : `$${(d.total / 1_000).toFixed(0)}k`
          return (
            <div
              key={`${d.mes}-${d.anio}`}
              className="relative flex flex-1 items-end rounded-sm bg-muted/20"
            >
              <span
                className="absolute left-0 right-0 text-center text-xs text-muted-foreground"
                style={{ bottom: `${barPx + 6}px` }}
              >
                {label}
              </span>
              <div
                aria-hidden="true"
                className="w-full rounded-t-sm bg-primary"
                style={{ height: `${barPx}px` }}
              />
            </div>
          )
        })}
      </div>
      <div className="mt-2 flex gap-3">
        {data.map((d) => (
          <div
            key={`${d.mes}-${d.anio}`}
            className="flex-1 text-center text-xs font-medium text-muted-foreground"
          >
            {MESES_CORTOS[d.mes - 1]}
          </div>
        ))}
      </div>
    </section>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-56 rounded-xl" />
      <Skeleton className="h-72 rounded-xl" />
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )
}
