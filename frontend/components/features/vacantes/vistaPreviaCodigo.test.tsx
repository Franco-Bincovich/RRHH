import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { VacanteCampoCodigo } from "./VacanteCampoCodigo"

/**
 * "Se va a usar: LIDER-DE-EQUIPO" — la vista previa de la conversión, debajo del campo.
 *
 * 🔴 POR QUÉ ESTO TIENE TEST PROPIO Y NO ES UN DETALLE DE ESTILO. El sistema guarda algo DISTINTO
 * de lo que la persona escribió: eso sólo es aceptable si lo muestra antes. Sin la vista previa,
 * Capital Humano escribe «Lider de equipo», el sistema guarda `LIDER-DE-EQUIPO`, el aviso se
 * publica con un código que nadie vio, y se enteran cuando un candidato pregunta por qué su CV no
 * llegó. **Convertir en silencio es peor que rechazar** — el rechazo por lo menos se ve.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. **Que el valor de entrada fuera ya canónico.** Con `value="LIDER-DE-EQUIPO"` la vista previa
 *    diría lo mismo que el input y un componente que simplemente repitiera `value` pasaría. Por
 *    eso todos los casos entran en texto natural y se afirma el resultado CONVERTIDO.
 * 2. **Que no se mirara el caso vacío.** Un componente que mostrara "Se va a usar:" siempre
 *    pondría el cartel con nada al lado antes de que se escriba la primera letra.
 *
 * ⚠️ `vitest` corre sin jsdom: esto renderiza a markup y lo lee. Alcanza porque la vista previa se
 * deriva del `value` en el render, no de un efecto — no hay estado propio que ejercitar.
 */

const markup = (value: string) =>
  renderToStaticMarkup(<VacanteCampoCodigo value={value} onChange={() => {}} />)

describe("la conversión se ve antes de guardar", () => {
  it.each([
    ["Lider de equipo", "LIDER-DE-EQUIPO"],
    ["Analista Sr.", "ANALISTA-SR"],
    ["Ecónomo 2026", "ECONOMO-2026"],
    ["Diseño UX/UI", "DISENO-UX-UI"],
  ])("con «%s» la pantalla dice %s", (escrito, canonico) => {
    const html = markup(escrito)
    expect(html).toContain("Se va a usar")
    expect(html).toContain(canonico)
  })

  it("y muestra el canónico aunque coincida con lo tipeado", () => {
    // No es una advertencia de "te lo cambié": es el contrato "esto es lo que se guarda".
    // Mostrarlo sólo cuando difiere obligaría a adivinar si el silencio significa "igual" o
    // "todavía no lo calculé".
    expect(markup("ECO-2026")).toContain("Se va a usar")
  })

  it("EL CONTRASTE: con el campo vacío no hay cartel", () => {
    expect(markup("")).not.toContain("Se va a usar")
  })

  it("ni con un texto del que no sale ningún código", () => {
    // "..." convierte a "", y "Se va a usar: " sin nada al lado no dice nada. El mensaje de error
    // del campo es el que explica qué falta.
    expect(markup("...")).not.toContain("Se va a usar")
  })

  it("el texto tipeado sigue siendo el del input, sin convertir", () => {
    // 🔴 La otra mitad: el input NO se reescribe mientras se escribe. Convertir el valor visible
    // pelearía con el cursor y con el autocorrector, y borraría lo que la persona quiso poner.
    expect(markup("Lider de equipo")).toContain('value="Lider de equipo"')
  })

  it("la vista previa se anuncia a los lectores de pantalla", () => {
    expect(markup("Lider de equipo")).toContain('aria-live="polite"')
  })

  it("el campo NO limita el largo al tipear", () => {
    // El input recibe TEXTO NATURAL, más largo que el código. Cortarlo al tipear frenaría la
    // tecla sin decir por qué — el mismo pecado en chico que convertir en silencio.
    expect(markup("Lider de equipo")).not.toContain("maxLength")
    expect(markup("Lider de equipo")).not.toContain("maxlength")
  })
})
