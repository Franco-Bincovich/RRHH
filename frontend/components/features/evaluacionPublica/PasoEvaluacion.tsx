import { CheckCircle2 } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"

import { PASOS } from "./_preguntas"

/**
 * La barra de progreso de la evaluación pública: en qué paso está, cuánto lleva y cuántas
 * preguntas tiene el paso.
 *
 * El porcentaje sale del PASO y no de las preguntas contestadas, que es lo que ya hacía: son tres
 * pasos de distinto largo y un porcentaje por pregunta avanzaría a saltos desparejos.
 */
export function ProgresoPasos({ paso }: { paso: number }) {
  const pct = Math.round(((paso + 1) / PASOS.length) * 100)
  return (
    <div className="mb-8">
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-medium text-foreground">
          Paso {paso + 1} de {PASOS.length} — {PASOS[paso].label}
        </span>
        <span className="tabular-nums text-muted-foreground">{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground">
        {PASOS[paso].total} pregunta{PASOS[paso].total !== 1 ? "s" : ""} en este paso
      </p>
    </div>
  )
}

/**
 * El cierre: la evaluación se envió y no hay nada más que hacer.
 *
 * 🔴 USA LOS PARES `--success-*` Y ANTES ERA `bg-emerald-100 dark:bg-emerald-900/30` con
 * `text-emerald-600 dark:text-emerald-400`. Eran cuatro colores escritos a mano para lo que la
 * paleta ya resuelve con dos tokens, y ninguno de los cuatro pasa por `app/contrasteTokens.test.ts`,
 * que mide los pares en los dos temas. Es además el mismo verde que `/horas` tenía escrito con
 * otras opacidades: dos pantallas públicas, dos verdes distintos para decir lo mismo.
 */
export function EvaluacionCompletada() {
  return (
    <div className="flex flex-col items-center gap-5 py-16 text-center animate-in fade-in-0 zoom-in-95 duration-500">
      <div className="flex size-24 items-center justify-center rounded-full border border-success-line bg-success-wash">
        <CheckCircle2 className="size-12 text-success" aria-hidden="true" />
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-foreground">¡Evaluación completada!</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          Tus respuestas fueron registradas correctamente. El equipo de Capital Humano procesará
          tus resultados y te notificará en los próximos días.
        </p>
      </div>
      <p className="text-xs text-muted-foreground">Podés cerrar esta pestaña.</p>
    </div>
  )
}

/**
 * El esqueleto mientras se verifica el link: la barra de progreso y las tarjetas de pregunta, con
 * la forma que van a tener con datos (§3).
 *
 * Reemplaza a un spinner con la leyenda "Verificando tu evaluación…". Un spinner centrado no dice
 * nada sobre lo que viene; el esqueleto evita además el salto de layout cuando llegan las
 * preguntas, que en un teléfono es medio scroll.
 */
export function EsqueletoEvaluacion() {
  return (
    <div>
      <div className="mb-8 space-y-2">
        <Skeleton shimmer className="h-5 w-56 rounded-md" />
        <Skeleton shimmer className="h-2 w-full rounded-full" />
        <Skeleton shimmer className="h-3 w-40 rounded-md" />
      </div>
      <div className="space-y-4">
        {[0, 1, 2].map((i) => <Skeleton key={i} shimmer className="h-[7.5rem] w-full rounded-xl" />)}
      </div>
    </div>
  )
}
