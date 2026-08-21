"use client"

import { useCallback, useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { Building2 } from "lucide-react"

import { AvisoError } from "@/components/ui/AvisoError"
import { Button } from "@/components/ui/button"
import { ErrorState } from "@/components/ui/ErrorState"
import {
  EsqueletoEvaluacion, EvaluacionCompletada, ProgresoPasos,
} from "@/components/features/evaluacionPublica/PasoEvaluacion"
import { PreguntasDelPaso } from "@/components/features/evaluacionPublica/PreguntasDelPaso"
import {
  PASOS, PREGUNTAS_COGNITIVAS, PREGUNTAS_SELF, PREGUNTAS_TECNICAS, faltanEnPaso,
} from "@/components/features/evaluacionPublica/_preguntas"
import { fetchEvaluacion, submitEvaluacion } from "@/services/assessment"
import type { LinkInfo, RespuestaItem } from "@/types/assessment"

type Estado = "cargando" | "link_invalido" | "activa" | "enviando" | "listo"

export default function AssessmentPublicPage() {
  const params = useParams()
  const token = params.token as string

  const [estado, setEstado] = useState<Estado>("cargando")
  const [errorLink, setErrorLink] = useState("")
  const [errorEnvio, setErrorEnvio] = useState("")
  const [link, setLink] = useState<LinkInfo | null>(null)
  const [paso, setPaso] = useState(0)
  const [self, setSelf] = useState<Record<number, number>>({})
  const [cognitivas, setCognitivas] = useState<Record<number, number>>({})
  const [tecnicas, setTecnicas] = useState<Record<number, number>>({})

  const verificar = useCallback(() => {
    setEstado("cargando")
    setErrorLink("")
    fetchEvaluacion(token)
      .then((info) => { setLink(info); setEstado("activa") })
      .catch((err: Error) => { setErrorLink(err.message); setEstado("link_invalido") })
  }, [token])

  useEffect(() => { verificar() }, [verificar])

  const faltan = [
    faltanEnPaso(PREGUNTAS_SELF.map((q) => q.id), self),
    faltanEnPaso(PREGUNTAS_COGNITIVAS.map((q) => q.id), cognitivas),
    faltanEnPaso(PREGUNTAS_TECNICAS.map((q) => q.id), tecnicas),
  ][paso]

  async function avanzar() {
    if (faltan > 0) return
    if (paso < PASOS.length - 1) { setPaso((p) => p + 1); return }

    const respuestas: RespuestaItem[] = [
      ...PREGUNTAS_SELF.map((q) => ({ tipo: "self" as const, pregunta_id: q.id, respuesta: self[q.id] })),
      ...PREGUNTAS_COGNITIVAS.map((q) => ({ tipo: "cognitivo" as const, pregunta_id: q.id, respuesta: cognitivas[q.id] })),
      ...PREGUNTAS_TECNICAS.map((q) => ({ tipo: "tecnico" as const, pregunta_id: q.id, respuesta: tecnicas[q.id] })),
    ]
    setEstado("enviando")
    setErrorEnvio("")
    try {
      await submitEvaluacion(token, respuestas)
      setEstado("listo")
    } catch (err: unknown) {
      /*
       * 🔴 UN ENVÍO FALLIDO NO BORRA LA EVALUACIÓN, y antes sí. El `catch` mandaba la pantalla al
       * estado de error, que reemplaza todo por "Evaluación no disponible": con un corte de red
       * al apretar "Finalizar", alguien que acababa de contestar diez preguntas las perdía todas
       * y no tenía forma de reintentar. Ahora vuelve a `activa` con las respuestas intactas y el
       * error en un aviso al lado del botón.
       */
      setErrorEnvio(err instanceof Error ? err.message : "No pudimos enviar tus respuestas.")
      setEstado("activa")
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex h-14 max-w-2xl items-center gap-2.5 px-4">
          <Building2 className="size-5 text-primary" aria-hidden="true" />
          <span className="font-semibold text-foreground">HR Karstec</span>
          <span className="text-muted-foreground">·</span>
          <span className="text-sm text-muted-foreground">Assessment</span>
          {link && (
            <>
              <span className="text-muted-foreground">·</span>
              <span className="truncate text-sm text-muted-foreground">{link.evaluado_nombre}</span>
            </>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-4 py-8">
        {estado === "cargando" && <EsqueletoEvaluacion />}

        {/*
         * 🔴 SIN REINTENTO, Y ES LA DIFERENCIA ENTRE LOS DOS ERRORES DE ESTA PANTALLA. Un link
         * inválido o ya usado no mejora reintentando: el botón prometería una salida que no
         * existe. El error de ENVÍO —que sí se puede reintentar— no pasa por acá: vive en un
         * `AvisoError` abajo, con las respuestas todavía en pantalla.
         */}
        {estado === "link_invalido" && (
          <ErrorState
            title="Evaluación no disponible"
            description={errorLink || "El link no es válido o ya fue utilizado."}
          />
        )}

        {(estado === "activa" || estado === "enviando") && (
          <>
            <ProgresoPasos paso={paso} />

            <PreguntasDelPaso
              paso={paso} self={self} cognitivas={cognitivas} tecnicas={tecnicas}
              onSelf={(id, v) => setSelf((p) => ({ ...p, [id]: v }))}
              onCognitiva={(id, v) => setCognitivas((p) => ({ ...p, [id]: v }))}
              onTecnica={(id, v) => setTecnicas((p) => ({ ...p, [id]: v }))}
            />

            {errorEnvio && <div className="mt-6"><AvisoError>{errorEnvio}</AvisoError></div>}

            <div className="mt-8 flex flex-wrap items-center justify-end gap-3">
              {/* Por qué la cuenta y no un botón mudo: ver `faltanEnPaso` en `_preguntas.ts`. */}
              {faltan > 0 && (
                <span className="text-sm text-muted-foreground">
                  Te {faltan === 1 ? "falta" : "faltan"} {faltan}{" "}
                  {faltan === 1 ? "respuesta" : "respuestas"}
                </span>
              )}
              <Button className="min-h-11 px-8" onClick={avanzar}
                disabled={faltan > 0 || estado === "enviando"}>
                {estado === "enviando"
                  ? "Enviando…"
                  : paso < PASOS.length - 1 ? "Siguiente" : "Finalizar evaluación"}
              </Button>
            </div>
          </>
        )}

        {estado === "listo" && <EvaluacionCompletada />}
      </main>
    </div>
  )
}
