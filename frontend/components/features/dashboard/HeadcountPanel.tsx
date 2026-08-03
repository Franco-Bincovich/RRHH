"use client"

import { Accordion } from "@base-ui/react/accordion"

import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { Badge } from "@/components/ui/badge"
import type { HeadcountArea } from "@/services/dashboard"
import { partirLista } from "./dashboardAdminData"

/**
 * Headcount por área. Extraído de DashboardAdmin.tsx al volverse plegable: la lista crece con
 * el organigrama (12 áreas con dos empresas cargadas, decenas con 500 empleados) y sin corte
 * la card se estira hasta empujar el resto del dashboard fuera de la pantalla.
 *
 * Las primeras CORTE_LISTA áreas se ven SIEMPRE (van en el `preview`) y el resto queda detrás
 * del desplegable, PLEGADO al entrar: un headcount es contexto, no una acción pendiente, y con
 * 12 áreas el corte esconde la mitad. El contador del encabezado dice el total, así que la card
 * nunca miente sobre cuántas áreas hay aunque se vean seis.
 *
 * Presentacional puro: sin estado, sin fetch. El orden lo trae el backend.
 */
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

export function HeadcountPanel({ areas }: { areas: HeadcountArea[] }) {
  // El máximo sale de TODAS las áreas, no de las visibles: si la escala se recalculara con el
  // corte, desplegar el resto cambiaría el largo de las barras de arriba.
  const max = Math.max(...areas.map((a) => a.total), 1)
  const { visibles, resto } = partirLista(areas)

  const barras = (filas: HeadcountArea[]) => (
    <div className="space-y-4">
      {filas.map((row) => <HeadcountBar key={row.area_id} {...row} max={max} />)}
    </div>
  )

  return (
    // `contents` deja que la card sea la celda de la grilla del dashboard y estire a la altura
    // de la fila, como cuando era un <section> suelto. El Root envuelve una sola sección, así
    // que no hace falta `multiple`.
    <Accordion.Root className="contents">
      <ConfigSection
        value="headcount"
        title="Headcount por área"
        badge={<Badge variant="secondary">{areas.length}</Badge>}
        disabled={resto.length === 0}
        preview={
          areas.length === 0
            ? <p className="text-sm text-muted-foreground">Sin datos de headcount.</p>
            : barras(visibles)
        }
      >
        {resto.length > 0 ? barras(resto) : null}
      </ConfigSection>
    </Accordion.Root>
  )
}
