"use client"

import { DollarSign, FileText, TrendingUp, Users } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import { MESES_CORTOS, MESES_LARGOS, pesos, varLabel } from "@/components/features/costos/formatos"
import type { DashboardCostos } from "@/types/costo"

/**
 * Los cuatro indicadores de la pantalla de Costos y la tarjeta que los dibuja.
 *
 * Salió de `costos/page.tsx` junto con el resto del corte. La tarjeta y el armado del array
 * viajaron JUNTOS a propósito: un KPI nuevo suma una entrada al array y nada más — tenerlos
 * separados obligaría a tocar dos archivos para agregar uno.
 *
 * 🔴 LOS CUATRO SALEN DE `dashboard`, QUE ES UN AGREGADO DEL BACKEND (`/api/costos/dashboard`).
 * Ninguno se deriva del detalle de nómina, que es la lista que pagina. Es la razón por la que
 * paginar esa lista no toca estos números — y la razón por la que no hay que "aprovechar" que la
 * nómina ya está en pantalla para calcular un KPI con ella: la página no es el total.
 */
function KpiCard({
  title,
  value,
  icon: Icon,
  description,
  accent,
}: {
  title: string
  value: string
  icon: LucideIcon
  description: string
  accent?: boolean
}) {
  return (
    <div className="rounded-xl border bg-card p-4 md:p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <span className="shrink-0 rounded-lg bg-primary/10 p-1.5 text-primary">
          <Icon className="size-4" />
        </span>
      </div>
      <p
        className={`mt-3 text-2xl font-bold tracking-tight ${
          accent ? "text-emerald-600 dark:text-emerald-400" : "text-foreground"
        }`}
      >
        {value}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{description}</p>
    </div>
  )
}

interface Props {
  dashboard: DashboardCostos
  mes: number
  anio: number
  totalEmpleados: number
}

export function KpisCostos({ dashboard, mes, anio, totalEmpleados }: Props) {
  const prevMes = mes === 1 ? 12 : mes - 1
  const prevAnio = mes === 1 ? anio - 1 : anio

  const kpis = [
    {
      title: "Costo total nómina",
      value: pesos(dashboard.total_nomina),
      icon: DollarSign,
      description: `Mensual bruto — ${MESES_LARGOS[mes - 1]} ${anio}`,
    },
    {
      title: "Costo promedio / colaborador",
      value: pesos(dashboard.costo_promedio),
      icon: Users,
      description: `Sobre ${totalEmpleados} colaboradores`,
    },
    {
      title: "Variación vs mes anterior",
      value: varLabel(dashboard.variacion_porcentual),
      icon: TrendingUp,
      description: `vs ${MESES_CORTOS[prevMes - 1]} ${prevAnio}`,
      accent: (dashboard.variacion_porcentual ?? 1) <= 0,
    },
    {
      title: "Áreas en nómina",
      value: String(dashboard.costos_por_area.length),
      icon: FileText,
      description: `${dashboard.costos_por_area.filter((a) => a.presupuesto > 0).length} con presupuesto cargado`,
    },
  ]

  return (
    <section aria-label="Indicadores de costos">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <KpiCard key={kpi.title} {...kpi} />
        ))}
      </div>
    </section>
  )
}
