import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { RadarChart } from "@/components/features/assessment/RadarChart"

import { AREAS_LABELS, AREAS_ORDER, AREAS_STYLE } from "./_areasAssessment"

function ProgressBar({ value, barColor }: { value: number; barColor: string }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
      <div className={`h-full rounded-full ${barColor} transition-all duration-500`} style={{ width: `${value}%` }} />
    </div>
  )
}

function ScoreCard({ dim, score }: { dim: string; score: number }) {
  const style = AREAS_STYLE[dim] ?? { bar: "bg-muted-foreground", bg: "bg-muted/30" }
  return (
    <div className={`rounded-xl border p-4 ${style.bg}`}>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold text-foreground">{AREAS_LABELS[dim] ?? dim}</h3>
        <Badge variant="outline">{score}/100</Badge>
      </div>
      <ProgressBar value={score} barColor={style.bar} />
    </div>
  )
}

/**
 * El radar del perfil AREAS y la grilla de scores por dimensión.
 *
 * Vivían adentro de `app/(dashboard)/assessment/[id]/page.tsx`. Se sacaron al agregar la barra de
 * identidad: la página estaba en 193 líneas contra un límite de 150 y tenía tres componentes
 * definidos adentro.
 *
 * ⚠️ EL RADAR PIDE AL MENOS TRES EJES, y no es un capricho: con dos, la figura es un segmento y
 * no comunica forma. Con menos, la sección directamente no se dibuja.
 *
 * 🔴 LA CLAVE `general` NO ES UNA DIMENSIÓN Y SE EXCLUYE ACÁ, que es de donde sale que el score
 * general viva en el chip de la barra de identidad: si se lo dejara entrar a esta grilla, se
 * leería como una sexta dimensión del mismo rango que las otras. Está anotado también en
 * `BarraAssessment`.
 */
export function ScoresSection({ scores }: { scores: Record<string, number> }) {
  const radarKeys = AREAS_ORDER.filter((k) => scores[k] !== undefined)
  const radarLabels = radarKeys.map((k) => AREAS_LABELS[k])
  const radarValues = radarKeys.map((k) => scores[k] ?? 0)
  const extra = Object.keys(scores).filter(
    (k) => !AREAS_ORDER.includes(k as (typeof AREAS_ORDER)[number]) && k !== "general",
  )
  const todas = [...radarKeys, ...extra]

  return (
    <>
      {radarValues.length >= 3 && (
        <Card as="section" aria-label="Perfil AREAS">
          <h2 className="mb-6 text-base font-semibold text-foreground">Perfil AREAS</h2>
          <div className="mx-auto max-w-sm">
            <RadarChart values={radarValues} labels={radarLabels} />
          </div>
          <div className="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {radarKeys.map((k, i) => (
              <div key={k} className="flex items-center justify-between rounded-lg border bg-muted/30 px-3 py-2 text-sm">
                <span className="text-muted-foreground">{radarLabels[i]}</span>
                <span className="font-semibold text-foreground">{radarValues[i]}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {todas.length > 0 && (
        <section>
          <h2 className="mb-4 text-base font-semibold text-foreground">Scores por dimensión</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {todas.map((k) => <ScoreCard key={k} dim={k} score={scores[k] ?? 0} />)}
          </div>
        </section>
      )}
    </>
  )
}
