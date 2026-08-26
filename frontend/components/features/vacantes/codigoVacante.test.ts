import { describe, expect, it } from "vitest"

import { EMPTY_VACANTE, payloadVacante, validateVacante } from "./vacanteForm"
import { CODIGO_MAX, CODIGO_MIN, normalizarCodigo, validarCodigo } from "./codigoVacante"

/**
 * La conversión del código de la búsqueda, del lado del navegador.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. 🔴 **Que los casos de entrada fueran códigos y no TÍTULOS.** Todo el primer bloque son
 *    textos como los escribe una persona —«Lider de equipo», «Analista Sr.»—, que es la feature:
 *    el CHECK anterior los rechazaba. Escritos ya en canónico, `normalizarCodigo` podría ser la
 *    identidad y pasaría igual.
 * 2. **Que faltaran los acentos y la ñ.** Son la única regla que no se puede desmentir con texto
 *    ASCII, y la más cara si se separa del backend: la vista previa diría una cosa y la base
 *    guardaría otra.
 * 3. **Que el payload mandara el valor CRUDO.** El último bloque compara lo que sale del form
 *    contra la forma canónica: sin él, `normalizarCodigo` podría existir sin estar cableada.
 *
 * ⚠️ La UNICIDAD no se prueba acá y no es un hueco: el front no la puede contestar sin mirar
 * todas las vacantes del sistema. Vive en el backend (`tests/test_vacante_codigo_unico.py`), que
 * además es el que abre este archivo para verificar que el espejo no se separó.
 */

describe("normalizarCodigo: de lo que escribe una persona al código", () => {
  it.each([
    ["Lider de equipo", "LIDER-DE-EQUIPO"],
    ["Analista Sr.", "ANALISTA-SR"],
    ["Ecónomo 2026", "ECONOMO-2026"],
    ["Diseño UX/UI", "DISENO-UX-UI"],
    ["  Jefe   de   Logística  ", "JEFE-DE-LOGISTICA"],
    ["Analista (Turno noche)", "ANALISTA-TURNO-NOCHE"],
    ["Ventas, Interior", "VENTAS-INTERIOR"],
    ["--eco-2026--", "ECO-2026"],
    ["ECO-2026", "ECO-2026"],
  ])("%s → %s", (escrito, esperado) => {
    expect(normalizarCodigo(escrito)).toBe(esperado)
  })

  it.each([
    ["Lider de equipo", "LIDER DE EQUIPO"],
    ["Lider de equipo", "lider.de.equipo"],
    ["Ecónomo 2026", "Economo 2026"],
  ])("«%s» y «%s» dan el MISMO código", (uno, otro) => {
    // Es la mitad de la unicidad: si no colapsaran, el segundo se guardaría como otra búsqueda.
    expect(normalizarCodigo(uno)).toBe(normalizarCodigo(otro))
  })

  it("no inventa un código donde no hay ninguno", () => {
    expect(normalizarCodigo("   ")).toBe("")
    expect(normalizarCodigo("---")).toBe("")
    expect(normalizarCodigo("()")).toBe("")
  })

  it("un texto a medio tipear se convierte igual, sin romperse", () => {
    // La pantalla lo muestra en vivo: cada tecla pasa por acá.
    expect(normalizarCodigo("L")).toBe("L")
    expect(normalizarCodigo("Lider de")).toBe("LIDER-DE")
  })
})

describe("validarCodigo: lo que no se puede usar, y por qué", () => {
  it.each([
    ["", "vacío"],
    ["   ", "sólo espacios"],
    ["..", "sólo puntuación"],
    ["Ñú", "muy corto (2 tras convertir)"],
    ["2026", "sólo números"],
    ["123 / 456", "sólo números con separadores"],
  ])("rechaza «%s» (%s)", (codigo) => {
    expect(validarCodigo(codigo)).toBeTruthy()
  })

  it.each([
    "Lider de equipo", "Analista Sr.", "Ecónomo 2026", "VAC-0001", "A1B",
    "Analista de Sistemas Semi Senior",
  ])("EL CONTRASTE: acepta «%s»", (codigo) => {
    expect(validarCodigo(codigo)).toBeUndefined()
  })

  it("el mensaje habla del CÓDIGO RESULTANTE, no del texto tipeado", () => {
    // 🔴 La pantalla muestra la conversión debajo del campo: nombrar el resultado es lo que
    // conecta lo que escribió con lo que el sistema entendió. "«ÑÚ» es muy corto" no se entiende.
    const msg = validarCodigo("Ñú")!
    expect(msg).toContain("«NU»")
    expect(msg).toContain(String(CODIGO_MIN))
  })

  it("el código de puros números tiene su PROPIO mensaje, no el genérico de forma", () => {
    // Es el rechazo menos evidente: `2026` se ve como un código perfectamente razonable.
    expect(validarCodigo("2026")!).toContain("letra")
  })
})

describe("pasarse del largo RECHAZA, no recorta", () => {
  const LARGO = "Responsable de Administracion y Finanzas del Grupo para la Region Centro"

  it("el máximo es 60 y una vacante REAL lo necesita", () => {
    // "Analista de Sistemas Semi Senior" es el título de VAC-0002 y canoniza a 32: con el techo
    // de 30 que puso la mig 122 no se podía cargar por su nombre.
    expect(CODIGO_MAX).toBe(60)
    expect(normalizarCodigo("Analista de Sistemas Semi Senior")).toHaveLength(32)
    expect(validarCodigo("Analista de Sistemas Semi Senior")).toBeUndefined()
  })

  it("un texto que se pasa se rechaza diciendo cuánto sobra", () => {
    const msg = validarCodigo(LARGO)!
    expect(msg).toContain(String(CODIGO_MAX))
    expect(msg.toLowerCase()).toContain("acortá")
  })

  it("y NO devuelve un código recortado", () => {
    // 🔴 Recortar produce dos códigos iguales a partir de textos distintos, y la segunda búsqueda
    // se rechazaría como duplicada de una que su autor nunca escribió.
    expect(normalizarCodigo(LARGO).length).toBeGreaterThan(CODIGO_MAX)
  })

  it("el caso concreto que justifica el rechazo", () => {
    const a = "Analista de Sistemas Senior con especializacion en datos"
    const b = "Analista de Sistemas Senior con especializacion en redes"
    expect(normalizarCodigo(a).slice(0, 30)).toBe(normalizarCodigo(b).slice(0, 30))
    expect(normalizarCodigo(a)).not.toBe(normalizarCodigo(b))
  })
})

describe("el form del alta usa la misma regla y manda el código convertido", () => {
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

  it("el payload viaja CONVERTIDO, no crudo", () => {
    expect(payloadVacante(form("Ecónomo 2026")).codigo).toBe("ECONOMO-2026")
  })

  it("EL CONTRASTE: con texto natural válido no hay error de código", () => {
    expect(validateVacante(form("Lider de equipo")).codigo).toBeUndefined()
  })
})
