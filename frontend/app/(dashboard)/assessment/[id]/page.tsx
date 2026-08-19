"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Download } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Card } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { RadarChart } from "@/components/features/assessment/RadarChart"
import { fetchResultado } from "@/services/assessment"
import type { ResultadoDetalle } from "@/types/assessment"

// ─── Constants ────────────────────────────────────────────────────────────────

const AREAS_ORDER = ["apertura", "responsabilidad", "estabilidad", "amabilidad", "sociabilidad"] as const
const AREAS_LABELS: Record<string, string> = {
  apertura:        "Apertura",
  responsabilidad: "Responsabilidad",
  estabilidad:     "Estabilidad",
  amabilidad:      "Amabilidad",
  sociabilidad:    "Sociabilidad",
  cognitivo:       "Cognitivo",
  tecnico:         "Técnico",
}
const AREAS_STYLE: Record<string, { bar: string; bg: string }> = {
  apertura:        { bar: "bg-blue-500",    bg: "bg-blue-50/50 dark:bg-blue-900/20"     },
  responsabilidad: { bar: "bg-emerald-500", bg: "bg-emerald-50/50 dark:bg-emerald-900/20" },
  estabilidad:     { bar: "bg-amber-500",   bg: "bg-amber-50/50 dark:bg-amber-900/20"   },
  amabilidad:      { bar: "bg-rose-500",    bg: "bg-rose-50/50 dark:bg-rose-900/20"     },
  sociabilidad:    { bar: "bg-purple-500",  bg: "bg-purple-50/50 dark:bg-purple-900/20" },
  cognitivo:       { bar: "bg-sky-500",     bg: "bg-sky-50/50 dark:bg-sky-900/20"       },
  tecnico:         { bar: "bg-teal-500",    bg: "bg-teal-50/50 dark:bg-teal-900/20"     },
}

// ─── Sub-components ───────────────────────────────────────────────────────────

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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AssessmentDetailPage() {
  const params  = useParams()
  const router  = useRouter()
  const id      = params.id as string

  const [resultado, setResultado] = useState<ResultadoDetalle | null>(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(false)
  // Módulo desactivado a propósito (no es un bug): redirige a /dashboard y no renderiza.
  // Es useState y NO const a propósito: un const colapsa a literal `false` por control-flow,
  // TS re-marca el cuerpo inalcanzable, se pierde el narrowing de `resultado` y `next build` falla.
  const [moduloActivo] = useState(false)

  useEffect(() => {
    if (!moduloActivo) { router.replace("/dashboard"); return }
    fetchResultado(id)
      .then(setResultado)
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [id, router, moduloActivo])

  if (!moduloActivo) return null

  function back() { router.push("/assessment") }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-24 w-full rounded-xl" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
        </div>
      </div>
    )
  }

  if (error || !resultado) {
    return (
      <div>
        <Button variant="ghost" size="sm" className="mb-4 min-h-11 gap-2" onClick={back}>
          <ArrowLeft className="size-4" /> Volver
        </Button>
        {error
          ? <ErrorState action={() => { setError(false); setLoading(true); fetchResultado(id).then(setResultado).catch(() => setError(true)).finally(() => setLoading(false)) }} />
          : <EmptyState icon={<ArrowLeft />} title="Resultado no encontrado" description="El perfil solicitado no existe o fue eliminado." />
        }
      </div>
    )
  }

  const scores        = resultado.scores ?? {}
  const radarKeys     = AREAS_ORDER.filter((k) => scores[k] !== undefined)
  const radarLabels   = radarKeys.map((k) => AREAS_LABELS[k])
  const radarValues   = radarKeys.map((k) => scores[k] ?? 0)
  const extraKeys     = Object.keys(scores).filter((k) => !AREAS_ORDER.includes(k as typeof AREAS_ORDER[number]) && k !== "general")
  const allDisplayKeys = [...AREAS_ORDER.filter((k) => scores[k] !== undefined), ...extraKeys]

  const metaParts = [
    `Tipo: ${resultado.tipo}`,
    resultado.area_nombre && `Área: ${resultado.area_nombre}`,
    resultado.posicion_objetivo && `Posición: ${resultado.posicion_objetivo}`,
    `Completado: ${resultado.fecha_completado ? new Date(resultado.fecha_completado).toLocaleDateString("es-AR") : "—"}`,
  ].filter(Boolean).join(" · ")

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" size="sm" className="mb-4 min-h-11 gap-2" onClick={back}>
          <ArrowLeft className="size-4" /> Volver a Assessment
        </Button>
      </div>

      <PageHeader
        title={resultado.evaluado_nombre || "Evaluado"}
        description={metaParts}
        action={
          <div className="flex items-center gap-2">
            {resultado.perfil_dominante && <Badge variant="outline">{resultado.perfil_dominante}</Badge>}
            {resultado.score_general != null && <Badge variant="default">Score {resultado.score_general}</Badge>}
          </div>
        }
      />

      {/* ── Radar ──────────────────────────────────────────────────────── */}
      {radarValues.length >= 3 && (
        <Card as="section">
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

      {/* ── Scores por dimensión ───────────────────────────────────────── */}
      {allDisplayKeys.length > 0 && (
        <section>
          <h2 className="mb-4 text-base font-semibold text-foreground">Scores por dimensión</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {allDisplayKeys.map((k) => (
              <ScoreCard key={k} dim={k} score={scores[k] ?? 0} />
            ))}
          </div>
        </section>
      )}

      {/* ── Descargar reportes ─────────────────────────────────────────── */}
      <Card as="section">
        <h2 className="mb-4 text-base font-semibold text-foreground">Descargar reportes</h2>
        <div className="flex flex-wrap gap-3">
          {(["Ejecutivo", "Comercial", "Competencias"] as const).map((tipo) => (
            <Button key={tipo} variant="outline" className="min-h-11 gap-2" disabled>
              <Download className="size-4" />
              Reporte {tipo}
            </Button>
          ))}
        </div>
      </Card>
    </div>
  )
}
