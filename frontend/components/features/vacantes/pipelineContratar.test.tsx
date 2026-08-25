/**
 * "Contratar" en el tablero de la vacante: la acción vive donde se mueve la etapa.
 *
 * 🔴 QUÉ CIERRA. Hasta el 25/8/2026 el botón existía SÓLO en el panel de detalle de /candidatos,
 * mientras las etapas se mueven acá: mover a alguien a Oferta y contratarlo cruzaba tres
 * pantallas, y nada en esta ficha lo indicaba. El porqué de la decisión —y por qué no se eligió
 * "que la ficha lo indique"— está escrito en `PipelineSeleccion`.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 * El padrón modela LOS DOS EJES por separado: alguien en `oferta` + `activo` (contratable), y
 * alguien en `oferta` + `descartado` (llegó hasta la oferta y la rechazó). Con un padrón donde
 * todos los de oferta estuvieran activos, "mira las dos condiciones" y "mira sólo la etapa"
 * darían el mismo verde — y ese es exactamente el bug que la condición existe para evitar.
 */
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { PipelineSeleccion } from "@/components/features/vacantes/PipelineSeleccion"
import type { Candidato } from "@/types/vacantes"

function cand(over: Partial<Candidato>): Candidato {
  return {
    id: "c1", vacante_id: "v1", nombre: "Ana", apellido: "Gómez", email: "a@x.com",
    cargo_anterior: null, empresa_anterior: null, etapa_pipeline: "oferta", estado: "activo",
    score_ia: null, clasificacion_ia: null, clasificacion_motivo: null, clasificacion_origen: null,
    cv_storage_path: null, screening_warning: null, created_at: "2026-08-01T00:00:00Z",
    ...over,
  }
}

function tablero(candidatos: Candidato[], canWrite = true): string {
  return renderToStaticMarkup(
    <PipelineSeleccion
      candidatos={candidatos} canWrite={canWrite} onMovido={() => {}} onRecargar={() => {}}
    />,
  )
}

describe("contratar se ofrece donde se movió la etapa", () => {
  it("en oferta y activo, el botón está en el tablero", () => {
    expect(tablero([cand({})])).toContain("Contratar")
  })

  it("en oferta pero descartado, NO se ofrece — y se ve por qué", () => {
    // Los dos ejes: llegó a la oferta (etapa) y no sigue en carrera (estado). Sin el chip, la
    // columna mostraría esta tarjeta idéntica a la de arriba.
    const html = tablero([cand({ id: "c2", estado: "descartado" })])
    expect(html).not.toContain("Contratar")
    expect(html).toContain("Descartado")
  })

  it("en una etapa anterior no se ofrece, aunque esté activo", () => {
    expect(tablero([cand({ etapa_pipeline: "entrevista_tecnica" })])).not.toContain("Contratar")
  })

  it("sin permiso de escritura no se ofrece", () => {
    expect(tablero([cand({})], false)).not.toContain("Contratar")
  })
})
