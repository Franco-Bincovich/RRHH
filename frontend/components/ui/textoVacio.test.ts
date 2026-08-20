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
