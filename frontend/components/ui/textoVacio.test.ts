import { describe, expect, it } from "vitest"

import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { textoVacio } from "@/components/ui/textoVacio"

/**
 * (d) El texto del vacío se arma con los VALORES REALES de los filtros activos.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDA FALLAR? Que el texto vuelva a ser genérico.
 * Verificado: devolviendo "No hay resultados" fijo, cinco de estos tests rojean.
 */

const chip = (etiqueta: string, valor: string): ChipFiltro => ({
  clave: etiqueta, etiqueta, valor, quitar: () => {},
})

describe("(d) el vacío nombra los filtros que lo causaron", () => {
  it("usa la empresa como sujeto y enumera el resto", () => {
    const { descripcion } = textoVacio(
      [chip("Empresa", "Bodegas Tupungato"), chip("Área", "Sistemas"), chip("Estado", "Baja")],
      "colaboradores",
      "Empresa",
    )
    expect(descripcion).toBe("Bodegas Tupungato no tiene colaboradores con área Sistemas y estado Baja.")
  })

  it("con un solo filtro además del sujeto no mete una 'y' colgada", () => {
    const { descripcion } = textoVacio([chip("Empresa", "Karstec"), chip("Estado", "Licencia")], "colaboradores", "Empresa")
    expect(descripcion).toBe("Karstec no tiene colaboradores con estado Licencia.")
  })

  it("sin sujeto, la frase arranca impersonal pero mantiene los valores", () => {
    const { descripcion } = textoVacio([chip("Área", "Sistemas")], "colaboradores", "Empresa")
    expect(descripcion).toBe("No hay colaboradores con área Sistemas.")
  })

  it("con la empresa como único filtro no queda 'con' sin nada atrás", () => {
    const { descripcion } = textoVacio([chip("Empresa", "Karstec")], "colaboradores", "Empresa")
    expect(descripcion).toBe("Karstec no tiene colaboradores cargados.")
  })

  it("🔴 sin filtros NO es 'no encontré': es 'todavía no hay'", () => {
    // Son dos pantallas distintas. Confundirlas manda al usuario a revisar filtros que no puso.
    const { titulo, descripcion } = textoVacio([], "colaboradores", "Empresa")
    expect(titulo).toBe("Todavía no hay colaboradores")
    expect(descripcion).not.toContain("filtro")
  })

  it("tres condiciones se enumeran con comas y una 'y' final", () => {
    const { descripcion } = textoVacio(
      [chip("Área", "Sistemas"), chip("Estado", "Baja"), chip("Liderazgo", "Solo líderes")],
      "colaboradores",
    )
    expect(descripcion).toContain("área Sistemas, estado Baja y liderazgo Solo líderes")
  })
})

/**
 * 🔴 EL GÉNERO DEL SUSTANTIVO — la frase concuerda en DOS lugares, no en uno.
 *
 * Hasta el 21/8/2026 las dos concordancias estaban en masculino fijo, y sobre siete de las quince
 * pantallas que usan este helper la frase quedaba mal escrita ("Cuando se cargue **el primero**"
 * sobre áreas, bajas, ausencias, vacantes, empresas, vacaciones y recategorizaciones; y "Karstec
 * no tiene áreas **cargados**", que es la MISMA falla en otra rama y no estaba a la vista).
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR? Que la función volviera a
 * escribir el literal masculino, o que atendiera una sola de las dos ramas. Las dos direcciones
 * están cubiertas —masculino Y femenino— porque con una sola, una función que devolviera siempre
 * femenino pasaría igual.
 */
describe("el género del sustantivo gobierna las DOS concordancias", () => {
  it("sin filtros: masculino por default, femenino cuando se lo pide", () => {
    expect(textoVacio([], "colaboradores").descripcion)
      .toBe("Cuando se cargue el primero va a aparecer acá.")
    expect(textoVacio([], "áreas", undefined, "femenino").descripcion)
      .toBe("Cuando se cargue la primera va a aparecer acá.")
  })

  it("con el sujeto como único filtro: 'cargados' o 'cargadas', por el MISMO parámetro", () => {
    // Ésta es la rama que apareció al arreglar la otra. Una sola decisión por pantalla gobierna
    // las dos, así que no se puede acertar una y errar la otra.
    expect(textoVacio([chip("Empresa", "Karstec")], "colaboradores", "Empresa").descripcion)
      .toBe("Karstec no tiene colaboradores cargados.")
    expect(textoVacio([chip("Empresa", "Karstec")], "áreas", "Empresa", "femenino").descripcion)
      .toBe("Karstec no tiene áreas cargadas.")
  })

  it("el género NO toca ninguna de las otras dos frases", () => {
    // Las ramas "con condiciones" no llevan participio ni ordinal: si el parámetro se colara ahí,
    // estaría cambiando texto que no tiene nada que concordar.
    const conCondiciones = textoVacio([chip("Área", "Sistemas")], "áreas", "Empresa", "femenino")
    expect(conCondiciones.descripcion).toBe("No hay áreas con área Sistemas.")
    const conSujeto = textoVacio(
      [chip("Empresa", "Karstec"), chip("Estado", "Baja")], "áreas", "Empresa", "femenino",
    )
    expect(conSujeto.descripcion).toBe("Karstec no tiene áreas con estado Baja.")
    // Y el título tampoco: "Todavía no hay X" no concuerda con nada.
    expect(textoVacio([], "áreas", undefined, "femenino").titulo).toBe("Todavía no hay áreas")
  })
})
