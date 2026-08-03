"use client"

import { Accordion } from "@base-ui/react/accordion"

import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { Badge } from "@/components/ui/badge"
import type { HeadcountArea } from "@/services/dashboard"

/**
 * Headcount por área. Extraído de DashboardAdmin.tsx al volverse plegable: la lista crece con
 * el organigrama (12 áreas con dos empresas cargadas, decenas con 500 empleados) y sin plegar
 * la card se estira hasta empujar el resto del dashboard fuera de la pantalla.
 *
 * 🔴 PLEGADA MUESTRA SOLO EL TÍTULO Y EL CONTADOR, sin ninguna fila asomando. Antes dejaba las
 * 6 primeras a la vista y eso ANULABA el acordeón: con 6 barras la card ocupa casi lo mismo que
 * con 12, así que se pagaba la complejidad del plegado sin recuperar la pantalla. El contador
 * del encabezado ya responde de un vistazo la pregunta que un asomo respondería —cuántas áreas
 * hay—, y el reparto entre ellas está a un click.
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
  // El `1` del final no es cosmético: es lo que evita dividir por cero cuando no hay áreas o
  // cuando todas están en 0. Sin él las barras saldrían con `width: NaN%`.
  const max = Math.max(...areas.map((a) => a.total), 1)

  return (
    // Sin `defaultValue`: arranca PLEGADA. Un headcount es contexto, no algo pendiente de hacer.
    // El Root envuelve una sola sección, así que no hace falta `multiple`.
    // (Tuvo `className="contents"` para que la card fuera la celda de la grilla y estirara a la
    // altura de la fila. Desde que la grilla lleva `items-start` no hay estiramiento que heredar,
    // así que el `contents` no hacía nada y se sacó: un `display:contents` que no se usa es un
    // mecanismo activo que el próximo que lo lea va a tener que descartar a mano.)
    <Accordion.Root>
      <ConfigSection
        value="headcount"
        title="Headcount por área"
        badge={<Badge variant="secondary">{areas.length}</Badge>}
      >
        {areas.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin datos de headcount.</p>
        ) : (
          <div className="space-y-4">
            {areas.map((row) => <HeadcountBar key={row.area_id} {...row} max={max} />)}
          </div>
        )}
      </ConfigSection>
    </Accordion.Root>
  )
}
