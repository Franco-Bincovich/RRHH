"use client"

import { Clock, Building2, Users, ListChecks } from "lucide-react"

import type { KPIsHoras } from "@/types/horasCliente"

/**
 * Los cuatro KPIs del encabezado. PRESENTACIONAL: sin estado, sin fetch, sin efectos.
 *
 * Se renderiza SIEMPRE, incluso con todo en cero: un mes sin cargas tiene que verse como "0
 * horas", no como una pantalla vacía en la que no se sabe si falló algo. Es el mismo criterio
 * del dashboard, donde un KPI que falla queda en cero y marcado, nunca ausente.
 */
export function KPIsHorasPanel({ kpis }: { kpis: KPIsHoras }) {
  const tarjetas = [
    { label: "Horas del mes", valor: kpis.horas_totales.toLocaleString("es-AR"), icon: Clock },
    { label: "Clientes con carga", valor: String(kpis.clientes_con_carga), icon: Building2 },
    { label: "Colaboradores que cargaron", valor: String(kpis.empleados_que_cargaron), icon: Users },
    { label: "Registros", valor: String(kpis.registros), icon: ListChecks },
  ]
  return (
    <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {tarjetas.map((t) => (
        <div key={t.label} className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <t.icon className="size-4" />
            <span className="text-xs">{t.label}</span>
          </div>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-foreground">{t.valor}</p>
        </div>
      ))}
    </div>
  )
}
