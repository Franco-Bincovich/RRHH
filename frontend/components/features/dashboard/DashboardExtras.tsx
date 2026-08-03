"use client"

import { Accordion } from "@base-ui/react/accordion"
import { Cake, PartyPopper } from "lucide-react"

import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { Badge } from "@/components/ui/badge"
import type { DistribItem, KpisExtra, PersonaFecha } from "@/services/dashboard"
import { partirLista } from "./dashboardAdminData"

// Paneles de KPIs 28 (distribución) y 30 (cumpleaños/aniversarios). Se suman al layout del
// dashboard admin sin rediseñarlo. Empty state coherente en cada bloque.
//
// SOLO la card de cumpleaños/aniversarios es plegable: sus dos listas traen una fila por
// empleado que cumple o festeja en el mes, o sea que crecen con la plantilla (~40 por columna
// con 500 empleados). La de distribución NO se toca: agrupa por seniority y tipo de contrato,
// que son categorías —un puñado, más "Sin especificar"— y no crecen con la gente.

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

/** Solo la lista. El empty state es del llamador: la cola de un corte vacía no muestra nada. */
function FechasLista({ items, icon: Icon }: { items: PersonaFecha[]; icon: typeof Cake }) {
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

function FechasColumna({ titulo, items, icon, vacio }: { titulo: string; items: PersonaFecha[]; icon: typeof Cake; vacio: string }) {
  return (
    <div>
      <h3 className="mb-3 text-sm font-medium text-muted-foreground">{titulo}</h3>
      {items.length === 0
        ? <p className="text-sm text-muted-foreground">{vacio}</p>
        : <FechasLista items={items} icon={icon} />}
    </div>
  )
}

export function DashboardExtras({ data }: { data: KpisExtra }) {
  const cumples = partirLista(data.cumpleanos_mes)
  const aniversarios = partirLista(data.aniversarios_mes)
  const ocultos = cumples.resto.length + aniversarios.resto.length
  const total = data.cumpleanos_mes.length + data.aniversarios_mes.length

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <section className="rounded-xl border bg-card p-4 md:p-6" aria-label="Distribución de plantilla">
        <h2 className="mb-5 text-base font-semibold text-foreground">Distribución de plantilla</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <DistribLista titulo="Por seniority" items={data.distribucion_seniority} />
          <DistribLista titulo="Por modalidad" items={data.distribucion_modalidad} />
        </div>
      </section>

      {/* Plegada al entrar (sin `defaultValue`): son efemérides, no algo pendiente de hacer.
          El contador suma las dos columnas — es "cuánta gente festeja este mes", que es la
          pregunta de la card; separarlo por columna repetiría lo que ya dicen los encabezados. */}
      <Accordion.Root className="contents">
        <ConfigSection
          value="fechas"
          title="Cumpleaños y aniversarios del mes"
          badge={<Badge variant="secondary">{total}</Badge>}
          disabled={ocultos === 0}
          preview={
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <FechasColumna titulo="Cumpleaños" items={cumples.visibles} icon={Cake} vacio="Sin cumpleaños este mes." />
              <FechasColumna titulo="Aniversarios de ingreso" items={aniversarios.visibles} icon={PartyPopper} vacio="Sin aniversarios este mes." />
            </div>
          }
        >
          {/* La cola repite la grilla para que cada resto caiga bajo SU columna. Sin encabezados
              ni empty state: los del preview, que está justo arriba, siguen a la vista. */}
          {ocultos > 0 ? (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>{cumples.resto.length > 0 && <FechasLista items={cumples.resto} icon={Cake} />}</div>
              <div>{aniversarios.resto.length > 0 && <FechasLista items={aniversarios.resto} icon={PartyPopper} />}</div>
            </div>
          ) : null}
        </ConfigSection>
      </Accordion.Root>
    </div>
  )
}
