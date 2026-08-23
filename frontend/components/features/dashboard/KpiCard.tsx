import Link from "next/link"

import { Card } from "@/components/ui/card"
import type { KpiCardData, TonoKpi } from "./_kpisDashboard"

/**
 * La card de un KPI del dashboard, y el esqueleto que ocupa su lugar mientras carga.
 *
 * Salió de `DashboardAdmin.tsx` (138/150) antes de sumarle el fondo semántico: el componente que
 * orquesta la pantalla no es el lugar donde se decide cómo se ve una card.
 *
 * 🔴 EL FONDO SE DESPEGA, EL NÚMERO NO. §6: *"el que requiere acción se despega con el fondo del
 * semántico que corresponda, no con un número en color"*. Un número en rojo se lee como parte del
 * dato —"perdimos plata"— y encima obliga a distinguir dos tonos de texto chico; el fondo se ve
 * de reojo desde el otro lado de la grilla y deja el número diciendo lo único que dice, que es
 * cuánto. Por eso el valor va SIEMPRE en `text-foreground`, en las cuatro variantes.
 * `KpiCard.test.tsx` lo fija: el wash tiene que estar en el contenedor y no en el <p>.
 */
interface EstiloTono {
  /** Borde + fondo de la card. */
  card: string
  /** El chip del ícono, que acompaña al fondo (un chip azul sobre ámbar se lee como un error). */
  chip: string
}

/**
 * Los cuatro tonos existen y hoy la pantalla usa DOS. No es código muerto por descuido: es la
 * paleta semántica del sistema de diseño, que ya está en `paleta.css` con su test de contraste
 * en los dos temas (`app/contrasteTokens.test.ts`). Lo que se decide card por card —y se
 * justifica en `_kpisDashboard.ts`— es CUÁL corresponde; hoy solo "Ingresos próximos 30 días"
 * se gana un tono, y esa parquedad es deliberada: si se despegan cinco, no se despega ninguna.
 */
const TONOS: Record<TonoKpi, EstiloTono> = {
  neutro: { card: "border-border bg-card", chip: "bg-primary/10 text-primary" },
  atencion: { card: "border-warning-line bg-warning-wash", chip: "bg-warning/10 text-warning" },
  riesgo: { card: "border-danger-line bg-danger-wash", chip: "bg-destructive/10 text-destructive" },
  bien: { card: "border-success-line bg-success-wash", chip: "bg-success/10 text-success" },
}

/**
 * 🔴 EL HOVER ES CONSECUENCIA DEL LINK, NO UN ADORNO — y por eso llega recién ahora.
 *
 * Acá vivía la nota inversa: *"sin `interactive` y sin hover, porque un KPI no lleva a ningún
 * lado — el día que un KPI navegue a su listado filtrado, esa card pasa a `<Card interactive>` y
 * ésta es la nota que hay que borrar"*. Ese día es hoy: nueve de las diez cards llevan a la
 * pantalla de donde sale el dato (`_destinosKpi.ts`), así que la elevación de 3px de §2 dejó de
 * prometer un click que no existe y pasó a ser la única señal de que sí existe.
 *
 * 🔴 Y ES CONDICIONAL, NO GLOBAL. La card SIN `href` —porque no tiene destino declarado, o porque
 * el rol no puede leer la sección destino— sigue siendo un `<div>` quieto. Ponerle el movimiento
 * a las diez habría vuelto a prometer el click que la nota vieja evitaba, ahora justo en las que
 * de verdad no llevan a ningún lado.
 *
 * ⚠️ El movimiento sale de `<Card interactive>` y no se escribe acá: `decisionesVisuales.test.ts`
 * barre el front entero para que nadie reimplemente el hover de tarjeta fuera de `card.tsx`.
 * `padding="sm"` es exactamente el `p-4 md:p-5` que este archivo tenía escrito a mano, y al
 * `bg-card` de la base lo pisa `tono.card` vía `cn()`/tailwind-merge — por eso los cuatro tonos
 * siguen dando cuatro fondos distintos.
 */
/** El interior de la card, idéntico lleve link o no: lo único que cambia es el envoltorio. */
function Contenido({ kpi }: { kpi: KpiCardData }) {
  const Icon = kpi.icon
  const tono = TONOS[kpi.tono]
  return (
    <>
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-muted-foreground">{kpi.title}</p>
        <span className={`shrink-0 rounded-lg p-1.5 ${tono.chip}`}>
          <Icon className="size-4" />
        </span>
      </div>
      <p className="mt-3 text-2xl font-bold tracking-tight tabular-nums text-foreground">{kpi.value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{kpi.description}</p>
      {/* El reparto de una card que agrupa (hoy: headcount por empresa). Va debajo del valor y en
          texto chico: es el detalle del número de arriba, no otro número. */}
      {kpi.detalle && kpi.detalle.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-border/60 pt-2.5" role="list">
          {kpi.detalle.map((d) => (
            <li key={d.etiqueta} className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 truncate text-xs text-muted-foreground" title={d.etiqueta}>
                {d.etiqueta}
              </span>
              <span className="shrink-0 text-xs font-medium tabular-nums text-foreground">{d.valor}</span>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

/**
 * ⚠️ DOS RAMAS Y NO UN SPREAD CONDICIONAL (`{...(href ? {as: Link, href} : {})}`), que fue el
 * primer intento: `Card` es genérico en `as`, así que sobre una UNIÓN de props TS infiere el
 * elemento del lado equivocado y exige `href` también en la rama sin link. Con dos ramas cada
 * una tipa contra su propio `as`, y de paso se lee de un vistazo cuál de las dos formas es.
 */
export function KpiCard({ kpi }: { kpi: KpiCardData }) {
  const comun = { padding: "sm" as const, className: TONOS[kpi.tono].card }
  // `as={Link}` en vez de envolver la card en un <a>: envolver mete un elemento entre la celda de
  // la grilla y la card, y ahí el stretch de la grilla deja de llegarle a la card.
  return kpi.href ? (
    <Card as={Link} href={kpi.href} interactive {...comun}><Contenido kpi={kpi} /></Card>
  ) : (
    <Card {...comun}><Contenido kpi={kpi} /></Card>
  )
}

/** Seis bloques: el alto de la grilla de Operación, que es la más larga de las dos. */
export function KpiSkeleton() {
  return (
    <div className="grid animate-pulse grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3, 4, 5, 6].map((i) => <div key={i} className="h-28 rounded-xl border bg-muted" />)}
    </div>
  )
}
