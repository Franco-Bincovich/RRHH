import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { Historial } from "@/components/ui/Historial"
import type { Recategorizacion } from "@/types/recategorizacion"

import { CeldaCambios } from "./CeldaCambios"
import { entradasHistorial, montoLegible, paresCambiados } from "./_cambios"

/**
 * (d) un par que no cambió no muestra "de → a", y (e) el chip "Vigente" va en uno solo.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * (d) El padrón tiene filas con las TRES combinaciones que se dan en producción: una que cambió
 * un solo campo **teniendo los otros dos `*_anterior` cargados** (el caso que rompe la
 * implementación ingenua), una que cambió los tres, y una primera recategorización sin ningún
 * valor previo. Con un solo caso —el de los tres campos llenos— una función que devolviera
 * siempre los tres pares pasaría en verde.
 *
 * (e) Se cuentan las OCURRENCIAS de "Vigente" en el markup, no su presencia: marcar todas las
 * entradas —que es el error obvio— pasa cualquier `toContain`. Y se compara la POSICIÓN contra
 * la segunda entrada, así una implementación que lo pusiera en la última también rojea.
 */

/**
 * 🔑 `rol_anterior` VIENE CARGADO Y `rol_nuevo` EN `null`. No es un padrón raro: es lo que el
 * backend devuelve siempre que un cambio no tocó el rol, porque copia el anterior de la cadena.
 * Comparar `anterior !== nuevo` marcaría esta fila como si el rol se hubiera borrado.
 */
const SOLO_SENIORITY: Recategorizacion = {
  id: "r-1", empleado_id: "e-1", empresa_id: "emp-1", fecha_efectiva: "2026-09-01",
  rol_anterior: "ANALISTA", rol_nuevo: null,
  seniority_anterior: "SEMI SENIOR", seniority_nueva: "SENIOR",
  categoria_anterior: "3", categoria_nueva: null,
  motivo: "Por antigüedad", impacto_salarial: "150000.50",
  registrado_por: null, registrado_por_nombre: "Ana Pérez",
  empleado_nombre: "Juan Gómez", empresa_nombre: "Karstec",
  created_at: "2026-09-01T10:00:00Z", updated_at: null,
}

const LOS_TRES: Recategorizacion = {
  ...SOLO_SENIORITY, id: "r-2", fecha_efectiva: "2026-05-01",
  rol_nuevo: "ANALISTA SENIOR", seniority_nueva: "SEMI SENIOR", categoria_nueva: "3",
  seniority_anterior: "JUNIOR", categoria_anterior: "2", rol_anterior: "ANALISTA JR",
  motivo: "Promoción",
}

/** La PRIMERA de la persona: no hay valores previos en ningún campo. */
const PRIMERA: Recategorizacion = {
  ...SOLO_SENIORITY, id: "r-3", fecha_efectiva: "2024-01-01",
  rol_anterior: null, rol_nuevo: "ANALISTA JR",
  seniority_anterior: null, seniority_nueva: null,
  categoria_anterior: null, categoria_nueva: null,
  motivo: "Ingreso",
}

describe("(d) solo se muestran los pares que cambiaron", () => {
  it("🔴 un campo con `*_anterior` cargado y valor nuevo en null NO produce par", () => {
    const pares = paresCambiados(SOLO_SENIORITY)
    expect(pares.map((p) => p.clave)).toEqual(["seniority"])
    expect(pares[0]).toMatchObject({ desde: "SEMI SENIOR", hasta: "SENIOR" })
  })

  it("y en el markup no aparece el rol anterior ni un 'null'", () => {
    const html = renderToStaticMarkup(<CeldaCambios pares={paresCambiados(SOLO_SENIORITY)} />)
    expect(html).toContain("SENIOR")
    expect(html).not.toContain("ANALISTA")   // el rol no cambió: no se dibuja
    expect(html).not.toContain("null")
  })

  it("cuando cambian los tres, salen los tres en orden rol → seniority → categoría", () => {
    expect(paresCambiados(LOS_TRES).map((p) => p.clave)).toEqual(["rol", "seniority", "categoria"])
  })

  it("🔴 sin valor previo se muestra el valor solo, SIN flecha", () => {
    // "— →" se leería como si antes hubiera habido algo que se borró.
    const pares = paresCambiados(PRIMERA)
    expect(pares).toHaveLength(1)
    expect(pares[0].desde).toBeNull()
    const html = renderToStaticMarkup(<CeldaCambios pares={pares} />)
    expect(html).toContain("ANALISTA JR")
    expect(html).not.toContain("cambia a")   // el aria-label de la flecha
  })

  it("con valor previo SÍ hay flecha: la contracara", () => {
    const html = renderToStaticMarkup(<CeldaCambios pares={paresCambiados(SOLO_SENIORITY)} />)
    expect(html).toContain("cambia a")
  })
})

describe("(e) el historial de la ficha marca Vigente en el más reciente", () => {
  const entradas = entradasHistorial([SOLO_SENIORITY, LOS_TRES, PRIMERA])
  const html = renderToStaticMarkup(<Historial entradas={entradas} vacio="vacío" />)

  it("hay exactamente UN chip Vigente, no uno por entrada", () => {
    expect((html.match(/Vigente/g) ?? []).length).toBe(1)
  })

  it("y está en la primera entrada, que es la más reciente", () => {
    expect(html.indexOf("Vigente")).toBeLessThan(html.indexOf("Promoción"))
  })

  it("una entrada por RECATEGORIZACIÓN, no una por par cambiado", () => {
    // Con una por par, el cambio que tocó los tres campos daría tres entradas y "Vigente"
    // quedaría en el rol dejando la seniority del MISMO cambio sin marcar, como si fuera vieja.
    expect(entradas).toHaveLength(3)
    expect(entradas[1].hasta).toBe("ANALISTA SENIOR · SEMI SENIOR · 3")
    expect(entradas[1].desde).toBe("ANALISTA JR · JUNIOR · 2")
  })

  it("el motivo va como detalle: en la ficha, después de 'qué cambió' viene 'por qué'", () => {
    expect(entradas[0].detalle).toBe("Por antigüedad")
  })

  it("la lista se conserva en el orden que llega, sin reordenar", () => {
    expect(entradas.map((e) => e.clave)).toEqual(["r-1", "r-2", "r-3"])
  })
})

describe("el impacto salarial", () => {
  it("🔴 se PARSEA antes de formatear: llega como string desde Pydantic", () => {
    // `"150000.40".toLocaleString()` devuelve el string tal cual — sin separador y sin error.
    // El valor NO pisa el borde de redondeo a propósito: acá se prueba el parseo, no el redondeo.
    expect(montoLegible("150000.40")).toBe("$150.000")
  })

  it("los centavos se redondean al peso, y `.50` sube", () => {
    // Declarado y no accidental: el impacto llega con dos decimales (`Decimal`) y la pantalla
    // muestra pesos enteros, así que la regla de redondeo tiene que ser una decisión visible.
    // Es la misma que usa `pesos()` del historial salarial, que es el otro monto de la ficha.
    expect(montoLegible("150000.50")).toBe("$150.001")
    expect(montoLegible("150000.49")).toBe("$150.000")
  })

  it("un monto negativo es válido y sale con su signo", () => {
    expect(montoLegible("-20000")).toBe("-$20.000")
  })

  it("null y vacío dan cadena vacía: quien llama decide qué significa", () => {
    expect(montoLegible(null)).toBe("")
    expect(montoLegible("")).toBe("")
  })

  it("y NUNCA lleva un signo de porcentaje (§7: el impacto porcentual no existe)", () => {
    expect(montoLegible("150000.40")).not.toContain("%")
  })
})
