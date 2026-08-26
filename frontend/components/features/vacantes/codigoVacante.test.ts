import { describe, expect, it } from "vitest"

import { EMPTY_VACANTE, payloadVacante, validateVacante } from "./vacanteForm"
import { normalizarCodigo, validarCodigo } from "./codigoVacante"

/**
 * La forma del código de la búsqueda, del lado del navegador.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. **Que la validación fuera sólo "requerido".** La mitad de los casos de acá son códigos NO
 *    vacíos que igual no sirven —`2026`, `ECÓ-2026`, `AB`—, y cada uno tiene un motivo concreto
 *    del lado del matcher. Un `if (!codigo)` pelado los dejaría pasar a todos y el rechazo
 *    llegaría del backend, después del viaje.
 * 2. **Que el payload mandara el valor CRUDO.** El último bloque compara lo que sale del form
 *    contra la forma canónica: sin él, `normalizarCodigo` podría existir y no estar cableada, y
 *    el mensaje de "ya lo usa X" hablaría de un código escrito distinto del que se ve.
 * 3. **Que los mensajes fueran genéricos.** Se afirma que cada uno trae un ejemplo usable: quien
 *    escribe el código por primera vez no tiene de dónde deducir la regla.
 *
 * ⚠️ La UNICIDAD no se prueba acá y no es un hueco: el front no la puede contestar sin mirar
 * todas las vacantes del sistema. Vive en el backend (`tests/test_vacante_codigo_unico.py`), que
 * además es el que abre este archivo para verificar que el espejo no se separó.
 */

describe("normalizarCodigo: todas estas formas son el mismo código", () => {
  it.each([
    "ECO-2026", "eco-2026", " eco-2026 ", "ECO 2026", "eco_2026", "ECO.2026", "ECO  -  2026",
    "--eco-2026--",
  ])("%s → ECO-2026", (escrito) => {
    expect(normalizarCodigo(escrito)).toBe("ECO-2026")
  })

  it("no inventa un código donde no hay ninguno", () => {
    expect(normalizarCodigo("   ")).toBe("")
    expect(normalizarCodigo("---")).toBe("")
  })
})

describe("validarCodigo: lo que no se puede usar, y por qué", () => {
  it.each([
    ["", "vacío"],
    ["   ", "sólo espacios"],
    ["AB", "muy corto"],
    ["A".repeat(31), "muy largo"],
    ["2026", "sólo números"],
    ["123-456", "sólo números con guion"],
    ["ECÓ-2026", "con acento"],
    ["ECO%26", "con comodín de ILIKE"],
  ])("rechaza %s (%s)", (codigo) => {
    expect(validarCodigo(codigo)).toBeTruthy()
  })

  it.each(["ECO-2026", "eco 2026", "LOG-01", "VAC-0001", "A1B", "ECO2026"])(
    "EL CONTRASTE: acepta %s", (codigo) => {
      expect(validarCodigo(codigo)).toBeUndefined()
    })

  it("el código de puros números tiene su PROPIO mensaje, no el genérico de forma", () => {
    // 🔴 Es el rechazo menos evidente de todos: `2026` se ve como un código perfectamente
    // razonable. El motivo (matchearía cualquier año suelto en un asunto) tiene que estar en el
    // mensaje o el usuario prueba `2027` y vuelve a fallar.
    const msg = validarCodigo("2026")!
    expect(msg).toContain("letra")
    expect(msg).toContain("ECO-2026")
  })

  it("todo mensaje trae un ejemplo utilizable o dice el límite concreto", () => {
    const malos = ["", "AB", "A".repeat(31), "2026", "ECÓ-2026"]
    malos.forEach((c) => {
      const msg = validarCodigo(c)!
      expect(msg, c).toBeTruthy()
      expect(/ECO-2026|\d/.test(msg), `sin ejemplo ni límite: ${msg}`).toBe(true)
    })
  })
})

describe("el form del alta usa la misma regla y manda el código normalizado", () => {
  const form = (codigo: string) => ({
    ...EMPTY_VACANTE, empresa_id: "e1", area_id: "a1", titulo: "Analista", codigo,
  })

  it("un alta sin código no pasa la validación del form", () => {
    expect(validateVacante(form("")).codigo).toBeTruthy()
  })

  it("y el mensaje es EL MISMO que el del campo suelto", () => {
    // Dos textos distintos para la misma regla enseñan dos reglas distintas.
    expect(validateVacante(form("2026")).codigo).toBe(validarCodigo("2026"))
  })

  it("el payload viaja NORMALIZADO, no crudo", () => {
    expect(payloadVacante(form(" eco 2026 ")).codigo).toBe("ECO-2026")
  })

  it("EL CONTRASTE: con un código válido no hay error de código", () => {
    expect(validateVacante(form("ECO-2026")).codigo).toBeUndefined()
  })
})
