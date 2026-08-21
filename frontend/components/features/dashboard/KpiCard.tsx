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
 * `dashboardBloques.test.tsx` lo fija: el wash tiene que estar en el contenedor y no en el <p>.
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
 * ⚠️ SIN `interactive` Y SIN HOVER, aunque §2 defina el movimiento para las tarjetas: **un KPI
 * no lleva a ningún lado.** Los diez son un número y su explicación; no hay pantalla de detalle
 * detrás de "Colaboradores activos" ni filtro que quede aplicado al apretarlo. La elevación al
 * apuntar es lo que dice "esto es un control" (ver el bloque de `components/ui/card.tsx`), así
 * que ponérsela acá prometería un click que no existe — y encima sobre la card con fondo
 * semántico, que es la que más invita a apretar. El día que un KPI navegue a su listado
 * filtrado, esa card pasa a `<Card interactive>` y ésta es la nota que hay que borrar.
 */
export function KpiCard({ kpi }: { kpi: KpiCardData }) {
  const Icon = kpi.icon
  const tono = TONOS[kpi.tono]
  return (
    <div className={`rounded-xl border p-4 md:p-5 ${tono.card}`}>
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
    </div>
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
