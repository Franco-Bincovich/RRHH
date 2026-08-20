"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { AlertCircle, Building2, CheckCircle2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { fetchEvaluacion, submitEvaluacion } from "@/services/assessment"
import type { LinkInfo, RespuestaItem } from "@/types/assessment"

// ─── Question data ────────────────────────────────────────────────────────────

interface LikertQuestion { id: number; texto: string }
interface Opcion         { id: number; texto: string }
interface McQuestion     { id: number; texto: string; opciones: Opcion[] }

const SELF_QUESTIONS: LikertQuestion[] = [
  { id: 1, texto: "Me adapto fácilmente a situaciones nuevas e impredecibles." },
  { id: 2, texto: "Suelo terminar lo que comienzo, incluso cuando resulta difícil." },
  { id: 3, texto: "Me mantengo calmado/a bajo presión o en situaciones de tensión." },
  { id: 4, texto: "Disfruto trabajar en equipo priorizando las necesidades del grupo." },
  { id: 5, texto: "Tomo la iniciativa cuando hay un problema que nadie está resolviendo." },
]

const COG_QUESTIONS: McQuestion[] = [
  { id: 1, texto: "¿Cuál es el siguiente número en la serie? 2, 6, 12, 20, 30, …",
    opciones: [{ id: 1, texto: "40" }, { id: 2, texto: "42" }, { id: 3, texto: "44" }, { id: 4, texto: "46" }] },
  { id: 2, texto: "Si todos los A son B, y algunos B son C, ¿qué podemos concluir?",
    opciones: [{ id: 1, texto: "Todos los A son C" }, { id: 2, texto: "Algunos A pueden ser C" }, { id: 3, texto: "Ningún A es C" }, { id: 4, texto: "Todos los C son A" }] },
  { id: 3, texto: "Un cuadrado se divide en 4 triángulos iguales y cada triángulo en 2. ¿Cuántos triángulos hay en total?",
    opciones: [{ id: 1, texto: "4" }, { id: 2, texto: "6" }, { id: 3, texto: "8" }, { id: 4, texto: "12" }] },
]

const TEC_QUESTIONS: McQuestion[] = [
  { id: 1, texto: "¿Qué es el 'product backlog' en metodología Scrum?",
    opciones: [{ id: 1, texto: "El historial de versiones del producto" }, { id: 2, texto: "Lista priorizada de funcionalidades pendientes" }, { id: 3, texto: "Los errores encontrados en producción" }, { id: 4, texto: "El equipo de desarrollo del producto" }] },
  { id: 2, texto: "¿Cuál es la diferencia principal entre REST API y GraphQL?",
    opciones: [{ id: 1, texto: "REST usa HTTP, GraphQL usa WebSockets" }, { id: 2, texto: "GraphQL permite solicitar exactamente los datos necesarios" }, { id: 3, texto: "REST es siempre más rápido que GraphQL" }, { id: 4, texto: "GraphQL solo funciona con JavaScript" }] },
]

const STEPS   = [
  { label: "Self Assessment",      total: SELF_QUESTIONS.length },
  { label: "Evaluación Cognitiva", total: COG_QUESTIONS.length  },
  { label: "Evaluación Técnica",   total: TEC_QUESTIONS.length  },
]
const LIKERT_LABELS = ["Muy en desacuerdo", "En desacuerdo", "Neutral", "De acuerdo", "Muy de acuerdo"]

// ─── Sub-components ───────────────────────────────────────────────────────────

function LikertRow({ question, selected, onSelect }: { question: LikertQuestion; selected: number | undefined; onSelect: (v: number) => void }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <p className="mb-4 text-sm font-medium text-foreground">{question.texto}</p>
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((v) => (
          <button key={v} onClick={() => onSelect(v)} aria-pressed={selected === v}
            className={cn("flex min-h-11 flex-1 items-center justify-center rounded-lg border text-sm font-semibold transition-colors",
              selected === v ? "border-primary bg-primary text-primary-foreground" : "border-border bg-background text-foreground hover:bg-muted")}>
            {v}
          </button>
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[10px] text-muted-foreground">
        <span>{LIKERT_LABELS[0]}</span>
        <span>{LIKERT_LABELS[4]}</span>
      </div>
    </div>
  )
}

function McRow({ question, selected, onSelect }: { question: McQuestion; selected: number | undefined; onSelect: (v: number) => void }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <p className="mb-4 text-sm font-medium text-foreground">{question.texto}</p>
      <div className="space-y-2">
        {question.opciones.map((opt) => (
          <button key={opt.id} onClick={() => onSelect(opt.id)} aria-pressed={selected === opt.id}
            className={cn("min-h-11 w-full rounded-lg border px-3 py-2.5 text-left text-sm transition-colors",
              selected === opt.id ? "border-primary bg-primary/10 text-foreground" : "border-border bg-background text-foreground hover:bg-muted")}>
            {opt.texto}
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

type PageState = "loading" | "error" | "active" | "submitting" | "done"

export default function AssessmentPublicPage() {
  const params = useParams()
  const token  = params.token as string

  const [pageState, setPageState]   = useState<PageState>("loading")
  const [errorMsg, setErrorMsg]     = useState<string>("")
  const [linkInfo, setLinkInfo]     = useState<LinkInfo | null>(null)
  const [step, setStep]             = useState(0)
  const [selfAnswers, setSelfAnswers] = useState<Record<number, number>>({})
  const [cogAnswers, setCogAnswers]   = useState<Record<number, number>>({})
  const [tecAnswers, setTecAnswers]   = useState<Record<number, number>>({})

  useEffect(() => {
    fetchEvaluacion(token)
      .then((info) => { setLinkInfo(info); setPageState("active") })
      .catch((err: Error) => { setErrorMsg(err.message); setPageState("error") })
  }, [token])

  function canAdvance(): boolean {
    if (step === 0) return SELF_QUESTIONS.every((q) => selfAnswers[q.id] !== undefined)
    if (step === 1) return COG_QUESTIONS.every((q) => cogAnswers[q.id] !== undefined)
    if (step === 2) return TEC_QUESTIONS.every((q) => tecAnswers[q.id] !== undefined)
    return false
  }

  async function advance() {
    if (!canAdvance()) return
    if (step < 2) { setStep((s) => s + 1); return }

    const respuestas: RespuestaItem[] = [
      ...SELF_QUESTIONS.map((q) => ({ tipo: "self" as const, pregunta_id: q.id, respuesta: selfAnswers[q.id] })),
      ...COG_QUESTIONS.map((q)  => ({ tipo: "cognitivo" as const, pregunta_id: q.id, respuesta: cogAnswers[q.id] })),
      ...TEC_QUESTIONS.map((q)  => ({ tipo: "tecnico" as const, pregunta_id: q.id, respuesta: tecAnswers[q.id] })),
    ]
    setPageState("submitting")
    try {
      await submitEvaluacion(token, respuestas)
      setPageState("done")
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Error al enviar respuestas")
      setPageState("error")
    }
  }

  const progressPct = Math.round(((step + 1) / 3) * 100)

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex h-14 max-w-2xl items-center gap-2.5 px-4">
          <Building2 className="size-5 text-primary" />
          <span className="font-semibold text-foreground">HR Karstec</span>
          <span className="text-muted-foreground">·</span>
          <span className="text-sm text-muted-foreground">Assessment</span>
          {linkInfo && (
            <>
              <span className="text-muted-foreground">·</span>
              <span className="text-sm text-muted-foreground">{linkInfo.evaluado_nombre}</span>
            </>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-4 py-8">
        {/* Loading */}
        {pageState === "loading" && (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <div className="size-10 animate-spin rounded-full border-4 border-muted border-t-primary" />
            <p className="text-sm text-muted-foreground">Verificando tu evaluación…</p>
          </div>
        )}

        {/* Error */}
        {pageState === "error" && (
          <div className="flex flex-col items-center gap-5 py-16 text-center">
            <div className="flex size-20 items-center justify-center rounded-full bg-destructive/10">
              <AlertCircle className="size-10 text-destructive" />
            </div>
            <div className="space-y-2">
              <h1 className="text-xl font-bold text-foreground">Evaluación no disponible</h1>
              <p className="max-w-sm text-sm text-muted-foreground">{errorMsg || "El link no es válido o ya fue utilizado."}</p>
            </div>
          </div>
        )}

        {/* Active / Submitting */}
        {(pageState === "active" || pageState === "submitting") && (
          <>
            <div className="mb-8">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="font-medium text-foreground">
                  Paso {step + 1} de 3 — {STEPS[step].label}
                </span>
                <span className="text-muted-foreground">{progressPct}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${progressPct}%` }} />
              </div>
              <p className="mt-1.5 text-xs text-muted-foreground">
                {STEPS[step].total} pregunta{STEPS[step].total !== 1 ? "s" : ""} en este paso
              </p>
            </div>

            {step === 0 && (
              <div className="space-y-4">
                <h1 className="text-xl font-bold text-foreground">Self Assessment</h1>
                <p className="text-sm text-muted-foreground">
                  Evaluá cada afirmación según tu nivel de acuerdo del 1 (muy en desacuerdo) al 5 (muy de acuerdo).
                </p>
                {SELF_QUESTIONS.map((q) => (
                  <LikertRow key={q.id} question={q} selected={selfAnswers[q.id]}
                    onSelect={(v) => setSelfAnswers((p) => ({ ...p, [q.id]: v }))} />
                ))}
              </div>
            )}

            {step === 1 && (
              <div className="space-y-4">
                <h1 className="text-xl font-bold text-foreground">Evaluación Cognitiva</h1>
                <p className="text-sm text-muted-foreground">Seleccioná la respuesta correcta para cada pregunta.</p>
                {COG_QUESTIONS.map((q) => (
                  <McRow key={q.id} question={q} selected={cogAnswers[q.id]}
                    onSelect={(v) => setCogAnswers((p) => ({ ...p, [q.id]: v }))} />
                ))}
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <h1 className="text-xl font-bold text-foreground">Evaluación Técnica</h1>
                <p className="text-sm text-muted-foreground">Respondé las siguientes preguntas sobre metodología y tecnología.</p>
                {TEC_QUESTIONS.map((q) => (
                  <McRow key={q.id} question={q} selected={tecAnswers[q.id]}
                    onSelect={(v) => setTecAnswers((p) => ({ ...p, [q.id]: v }))} />
                ))}
              </div>
            )}

            <div className="mt-8 flex justify-end">
              <Button className="min-h-11 px-8" onClick={advance}
                disabled={!canAdvance() || pageState === "submitting"}>
                {pageState === "submitting" ? "Enviando…" : step < 2 ? "Siguiente" : "Finalizar evaluación"}
              </Button>
            </div>
          </>
        )}

        {/* Done */}
        {pageState === "done" && (
          <div className="flex flex-col items-center gap-5 py-16 text-center animate-in fade-in-0 zoom-in-95 duration-500">
            <div className="flex size-24 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
              <CheckCircle2 className="size-12 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div className="space-y-2">
              <h1 className="text-2xl font-bold text-foreground">¡Evaluación completada!</h1>
              <p className="max-w-sm text-sm text-muted-foreground">
                Tus respuestas fueron registradas correctamente. El equipo de Capital Humano procesará tus resultados y te notificará en los próximos días.
              </p>
            </div>
            <p className="text-xs text-muted-foreground">Podés cerrar esta pestaña.</p>
          </div>
        )}
      </main>
    </div>
  )
}
