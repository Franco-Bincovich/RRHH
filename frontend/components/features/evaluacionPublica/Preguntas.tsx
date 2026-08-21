import { cn } from "@/lib/utils"

import { ETIQUETAS_LIKERT, type PreguntaLikert, type PreguntaMultiple } from "./_preguntas"

/**
 * Las dos formas de pregunta de la evaluación pública: la escala de 1 a 5 y la opción múltiple.
 *
 * 🔴 LOS BLANCOS SON DE 44px Y ESO NO ES OPCIONAL ACÁ. Esta pantalla la contesta alguien de afuera
 * del equipo, casi siempre desde el teléfono, y son 10 preguntas: un blanco chico no molesta una
 * vez, molesta diez. Los cinco botones de la escala se reparten el ancho (`flex-1`) y toman el
 * alto de `min-h-11`; los de opción múltiple ocupan el ancho completo.
 *
 * `aria-pressed` y no `role="radio"`: son botones de alternancia dentro de un grupo y el estado
 * seleccionado se comunica igual, sin tener que implementar a mano la navegación con flechas que
 * un radiogroup real exige.
 */
export function FilaLikert({ pregunta, elegido, onElegir }: {
  pregunta: PreguntaLikert
  elegido: number | undefined
  onElegir: (v: number) => void
}) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <p className="mb-4 text-sm font-medium text-foreground">{pregunta.texto}</p>
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => onElegir(v)}
            aria-pressed={elegido === v}
            aria-label={`${v} — ${ETIQUETAS_LIKERT[v - 1]}`}
            className={cn(
              "flex min-h-11 flex-1 items-center justify-center rounded-lg border text-sm font-semibold transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              elegido === v
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-background text-foreground hover:bg-muted",
            )}
          >
            {v}
          </button>
        ))}
      </div>
      {/* Sólo los extremos: son los que anclan la escala. Los cinco textos completos no entran en
          un teléfono sin partirse en dos renglones cada uno. El valor de cada botón lo dice su
          `aria-label`, así que quien usa lector de pantalla sí escucha los cinco. */}
      <div className="mt-1.5 flex justify-between text-[10px] text-muted-foreground">
        <span>{ETIQUETAS_LIKERT[0]}</span>
        <span>{ETIQUETAS_LIKERT[4]}</span>
      </div>
    </div>
  )
}

export function FilaMultiple({ pregunta, elegido, onElegir }: {
  pregunta: PreguntaMultiple
  elegido: number | undefined
  onElegir: (v: number) => void
}) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <p className="mb-4 text-sm font-medium text-foreground">{pregunta.texto}</p>
      <div className="space-y-2">
        {pregunta.opciones.map((opt) => (
          <button
            key={opt.id}
            type="button"
            onClick={() => onElegir(opt.id)}
            aria-pressed={elegido === opt.id}
            className={cn(
              "min-h-11 w-full rounded-lg border px-3 py-2.5 text-left text-sm transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              elegido === opt.id
                ? "border-primary bg-primary/10 text-foreground"
                : "border-border bg-background text-foreground hover:bg-muted",
            )}
          >
            {opt.texto}
          </button>
        ))}
      </div>
    </div>
  )
}
