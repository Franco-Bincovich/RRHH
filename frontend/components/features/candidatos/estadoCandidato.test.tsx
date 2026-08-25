import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { CandidatoRow } from "./CandidatoRow"
import { EstadoCandidatoBadge } from "./EstadoCandidatoBadge"
import type { CandidatoConGrupo, EstadoCandidato } from "@/types/candidato"

/**
 * La tarjeta de un candidato dice CÓMO TERMINÓ, no sólo dónde llegó.
 *
 * 🔴 EL BUG: se contrata a alguien y la tarjeta sigue diciendo **Oferta**. No era falta de
 * refresco —`onContratado` ya hacía `refetch()` y los datos llegaban correctos— sino que la fila
 * pintaba UN SOLO EJE de los dos, y justamente el que contratar NO cambia. `estado` viajaba por
 * HTTP, estaba tipado en `types/candidato.ts`, y su único uso en TODO el front era el booleano
 * `contratable` de `CandidatoAcciones`: **no se renderizaba en ningún lado**.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FIXTURE PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *   · 🔴 **La etapa se queda en `oferta` en TODOS los casos**, que es lo que hace producción
 *     (`services/_candidato_contratar.py` no toca `etapa_pipeline`, y está escrito ahí por qué).
 *     Un fixture que moviera la etapa junto con el estado —lo "natural" de inventar— haría que
 *     "muestra el desenlace" y "muestra la etapa" dieran el mismo resultado, y borrar el badge
 *     nuevo quedaría en verde. Es el caso #1 del manual del repo: el fake tiene que modelar la
 *     única diferencia que importa.
 *   · Se renderiza el markup REAL con `renderToStaticMarkup`. Sin jsdom no hay interacción, pero
 *     un badge es markup estático: es exactamente lo que esta suite sí puede ver.
 */

const BASE: CandidatoConGrupo = {
  id: "c1", vacante_id: "v1", nombre: "Ana", apellido: "Gómez", email: "ana@mail.com",
  telefono: null, cargo_anterior: null, empresa_anterior: null,
  // 🔴 SIEMPRE "oferta" — ver el ⚠️ del encabezado. No es un valor de relleno.
  etapa_pipeline: "oferta",
  estado: "activo",
  score_ia: null, busqueda_congelada: null, cv_storage_path: null, screening_warning: null,
  clasificacion_ia: null, clasificacion_motivo: null, clasificacion_origen: null,
  created_at: "2026-08-01T10:00:00Z", grupo_nombre: "Analista contable", busqueda_activa: true,
}

const fila = (estado: EstadoCandidato) =>
  renderToStaticMarkup(<CandidatoRow candidato={{ ...BASE, estado }} onSelect={() => {}} />)

describe("🔴 La fila muestra el desenlace, no sólo la etapa", () => {
  it("contratado: la tarjeta lo dice, con la etapa en oferta", () => {
    const html = fila("contratado")
    expect(html).toContain("Contratado")
    // La etapa NO desaparece: las dos son ciertas y dicen cosas distintas. Borrarla sacaría de
    // la pantalla el dato del embudo, que es justo lo que el backend se cuida de no pisar.
    expect(html).toContain("Oferta")
  })

  it("descartado y en espera también se ven", () => {
    expect(fila("descartado")).toContain("Descartado")
    expect(fila("en_espera")).toContain("En espera")
  })

  it("activo NO pinta nada: es el estado de casi todas las filas", () => {
    // La contracara. Sin esto, un badge que se pintara siempre pasaría los tests de arriba y
    // llenaría el listado de "Activo" — ruido en todas las filas, información en ninguna.
    const html = fila("activo")
    expect(html).toContain("Oferta")
    expect(html).not.toContain("Activo")
  })

  it("el badge suelto devuelve null con activo", () => {
    expect(renderToStaticMarkup(<EstadoCandidatoBadge estado="activo" />)).toBe("")
  })

  it("ningún estado se muestra con su literal crudo del CHECK", () => {
    // `en_espera` con guión bajo en pantalla es el síntoma de que faltó traducir el vocabulario.
    for (const estado of ["contratado", "descartado", "en_espera"] as EstadoCandidato[]) {
      expect(renderToStaticMarkup(<EstadoCandidatoBadge estado={estado} />)).not.toContain("en_espera")
    }
  })
})
