"use client"

import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ContratarCandidatoButton } from "@/components/features/candidatos/ContratarCandidatoButton"
import { EstadoCandidatoBadge } from "@/components/features/candidatos/EstadoCandidatoBadge"
import { CandidatoAccionesPipeline } from "@/components/features/screening/CandidatoAccionesPipeline"
import { CandidatoCard } from "@/components/features/vacantes/CandidatoCard"
import { formatFecha } from "@/components/features/shared/fechas"
import { moverCandidato } from "@/services/vacantes"
import type { Candidato, EtapaPipeline } from "@/types/vacantes"

import { ETAPA_COLUMN_BG, ETAPA_DOT, ETAPA_LABELS, ETAPAS } from "./_pipelineEtapas"

/** "Analista · Acme" o "Sin datos": lo que hacía antes, para ubicarlo sin abrir el CV. */
const cargoAnterior = (c: Candidato): string =>
  [c.cargo_anterior, c.empresa_anterior].filter(Boolean).join(" · ") || "Sin datos"

/**
 * El tablero de selección de una vacante: una columna por etapa, las tarjetas de los candidatos y
 * el botón que los mueve a la etapa siguiente.
 *
 * Vivía adentro de `app/(dashboard)/vacantes/[id]/page.tsx` (452 líneas). Se sacó al cortar esa
 * página, junto con el estado `moviendo` que sólo este tablero usa.
 *
 * 🔴 EL CONTADOR TOTAL NO ESTÁ ACÁ, y no se perdió: subió a la barra de identidad de la ficha,
 * que es donde se lee sin scrollear el tablero. Acá quedan los contadores POR COLUMNA, que dicen
 * otra cosa —dónde está la gente— y no se pueden reemplazar por el total.
 *
 * ⚠️ UN ERROR AL MOVER NO SE AVISA, tal como estaba antes de la división: el `catch` deja la
 * tarjeta donde estaba y no dice nada. No se cambió acá porque avisar bien pide decidir qué se
 * dice y si se reintenta, y eso es una decisión de producto. Queda anotado.
 */
export function PipelineSeleccion({ candidatos, canWrite, onMovido, onRecargar }: {
  candidatos: Candidato[]
  canWrite: boolean
  /** Reemplaza al candidato movido en la lista del caller: el tablero no es dueño de los datos. */
  onMovido: (candidato: Candidato) => void
  /**
   * Recarga la ficha entera. Es DISTINTO de `onMovido` y los dos hacen falta: mover una tarjeta
   * devuelve el candidato actualizado y alcanza con reemplazarlo, pero corregir una clasificación
   * desde `CandidatoAccionesPipeline` no devuelve nada — hay que volver a pedir. Colapsar los dos
   * en uno dejaría la corrección sin efecto visible hasta recargar la página a mano.
   */
  onRecargar: () => void
}) {
  const [moviendo, setMoviendo] = useState<string | null>(null)

  async function mover(candidatoId: string, etapa: EtapaPipeline) {
    setMoviendo(candidatoId)
    try {
      onMovido(await moverCandidato(candidatoId, etapa))
    } catch {
      // silently ignore — the UI stays in previous state
    } finally {
      setMoviendo(null)
    }
  }

  return (
    <div className="overflow-x-auto pb-4">
      <div className="flex gap-4" style={{ width: "max-content" }}>
        {ETAPAS.map((etapa) => {
          const cards = candidatos.filter((c) => c.etapa_pipeline === etapa)
          const siguiente = ETAPAS[ETAPAS.indexOf(etapa) + 1]
          return (
            <div key={etapa} className={`flex w-72 flex-shrink-0 flex-col rounded-xl p-3 ${ETAPA_COLUMN_BG[etapa]}`}>
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`size-2 rounded-full ${ETAPA_DOT[etapa]}`} />
                  <span className="text-sm font-semibold text-foreground">{ETAPA_LABELS[etapa]}</span>
                </div>
                <Badge variant="secondary">{cards.length}</Badge>
              </div>
              <div className="flex flex-col gap-2">
                {cards.map((c) => (
                  <div key={c.id}>
                    <CandidatoCard
                      nombre={`${c.nombre} ${c.apellido}`}
                      cargoAnterior={cargoAnterior(c)}
                      fechaAplicacion={formatFecha(c.created_at)}
                      etapa={c.etapa_pipeline}
                      clasificacion={c.clasificacion_ia}
                      motivo={c.clasificacion_motivo}
                      origen={c.clasificacion_origen}
                      sinTexto={Boolean(c.screening_warning)}
                      fallo={!c.clasificacion_ia && Boolean(c.clasificacion_motivo)}
                    />
                    {/* Ver CV + corregir la clasificación SIN salir de esta pantalla. */}
                    <CandidatoAccionesPipeline candidato={c} onCambio={onRecargar} />

                    {/* 🔴 CÓMO TERMINÓ, no sólo hasta dónde llegó: `etapa_pipeline` no se toca
                        al contratar ni al descartar (es la métrica del embudo), así que sin este
                        chip "Oferta" muestra igual al que sigue en carrera y al que ya se fue.
                        No pinta nada si el estado es `activo` — ver `EstadoCandidatoBadge`. */}
                    {c.estado !== "activo" && (
                      <div className="mt-1"><EstadoCandidatoBadge estado={c.estado} /></div>
                    )}
                    {/*
                     * 🔴 "CONTRATAR" VIVE ACÁ DESDE EL 25/8/2026, Y ESTE ES EL PUNTO DEL CAMBIO.
                     * Antes el botón existía SÓLO en el panel de detalle de /candidatos, y las
                     * etapas se mueven acá: el circuito completo —mover a Oferta, ir a otra
                     * pantalla, encontrar a la persona, abrir su panel, contratar— cruzaba tres
                     * pantallas y nada en esta ficha lo indicaba.
                     *
                     * De las dos salidas posibles se eligió ÉSTA (el botón donde se movió la
                     * etapa) y no "que la ficha lo indique", por tres razones:
                     *   · Contratar es la CONSECUENCIA inmediata de mover a alguien a Oferta, y
                     *     quien mueve la tarjeta es quien toma esa decisión. La acción pertenece
                     *     al lugar donde se decide.
                     *   · Un cartel que explica dónde está el botón es peor que el botón: deja
                     *     el recorrido de tres pantallas y le suma texto.
                     *   · No duplica nada: es el MISMO componente que usa /candidatos, con la
                     *     misma condición (`oferta` + `activo`), que el backend revalida igual.
                     * El de /candidatos NO se saca: ahí se llega por persona y no por búsqueda, y
                     * es la única puerta para un candidato sin vacante viva. */}
                    {canWrite && etapa === "oferta" && c.estado === "activo" && (
                      <div className="mt-1">
                        <ContratarCandidatoButton candidato={c} onContratado={onRecargar} />
                      </div>
                    )}

                    {canWrite && siguiente && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="mt-1 h-7 w-full text-xs text-muted-foreground"
                        disabled={moviendo === c.id}
                        onClick={() => mover(c.id, siguiente)}
                      >
                        {moviendo === c.id ? "Moviendo..." : `→ ${ETAPA_LABELS[siguiente]}`}
                      </Button>
                    )}
                  </div>
                ))}
                {cards.length === 0 && (
                  <div className="rounded-lg border border-dashed border-border bg-background/50 p-4 text-center text-xs text-muted-foreground">
                    Sin candidatos
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
