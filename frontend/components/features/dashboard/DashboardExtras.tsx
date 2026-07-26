"use client"

import { Cake, PartyPopper } from "lucide-react"

import type { DistribItem, KpisExtra, PersonaFecha } from "@/services/dashboard"

// Paneles de KPIs 28 (distribución) y 30 (cumpleaños/aniversarios). Se suman al layout del
// dashboard admin sin rediseñarlo. Empty state coherente en cada bloque.

function DistribLista({ titulo, items }: { titulo: string; items: DistribItem[] }) {
  return (
    <div>
      <h3 className="mb-3 text-sm font-medium text-muted-foreground">{titulo}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin datos.</p>
      ) : (
        <ul className="space-y-2" role="list">
          {items.map((d) => (
            <li key={d.categoria} className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 truncate text-sm text-foreground" title={d.categoria}>{d.categoria}</span>
              <span className="shrink-0 text-sm font-medium text-foreground">{d.total}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function FechasLista({ items, icon: Icon, vacio }: { items: PersonaFecha[]; icon: typeof Cake; vacio: string }) {
  if (items.length === 0) return <p className="text-sm text-muted-foreground">{vacio}</p>
  return (
    <ul className="divide-y divide-border" role="list">
      {items.map((p, i) => (
        <li key={i} className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0">
          <Icon className="size-4 shrink-0 text-muted-foreground" />
          <span className="min-w-0 flex-1 truncate text-sm text-foreground">{p.empleado}</span>
          <span className="shrink-0 text-sm text-muted-foreground">{p.fecha}</span>
        </li>
      ))}
    </ul>
  )
}

export function DashboardExtras({ data }: { data: KpisExtra }) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <section className="rounded-xl border bg-card p-4 md:p-6" aria-label="Distribución de plantilla">
        <h2 className="mb-5 text-base font-semibold text-foreground">Distribución de plantilla</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <DistribLista titulo="Por seniority" items={data.distribucion_seniority} />
          <DistribLista titulo="Por modalidad" items={data.distribucion_modalidad} />
        </div>
      </section>

      <section className="rounded-xl border bg-card p-4 md:p-6" aria-label="Cumpleaños y aniversarios del mes">
        <h2 className="mb-5 text-base font-semibold text-foreground">Cumpleaños y aniversarios del mes</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <h3 className="mb-3 text-sm font-medium text-muted-foreground">Cumpleaños</h3>
            <FechasLista items={data.cumpleanos_mes} icon={Cake} vacio="Sin cumpleaños este mes." />
          </div>
          <div>
            <h3 className="mb-3 text-sm font-medium text-muted-foreground">Aniversarios de ingreso</h3>
            <FechasLista items={data.aniversarios_mes} icon={PartyPopper} vacio="Sin aniversarios este mes." />
          </div>
        </div>
      </section>
    </div>
  )
}
