import { describe, expect, it } from "vitest"

import type { HistorialSalarialItem } from "@/types/costo"

import { cambiosSalariales, resumenSerie } from "./_cambiosSalariales"

/**
 * La serie mensual de sueldos → la lista de cambios que dibuja el historial.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDA FALLAR? Que se dejara de colapsar (vuelven las
 * 12 filas iguales), que se colapsara de más (se pierde un aumento), o que se comparara el neto
 * en vez del bruto (aparecen aumentos que nadie dio, por cambios de retención).
 */

const mes = (anio: number, m: number, bruto: number, neto = bruto * 0.8): HistorialSalarialItem =>
  ({ anio, mes: m, monto_bruto: bruto, monto_neto: neto })

// Como la devuelve el backend: más reciente primero.
const SERIE = [
  mes(2026, 5, 120_000),
  mes(2026, 4, 100_000),
  mes(2026, 3, 100_000),
  mes(2026, 2, 100_000),
  mes(2026, 1, 80_000),
]

describe("cambiosSalariales", () => {
  const cambios = cambiosSalariales(SERIE)

  it("colapsa los meses sin cambio: 5 períodos, 3 cambios", () => {
    expect(cambios).toHaveLength(3)
    expect(cambios.map((c) => c.fecha)).toEqual(["Mayo 2026", "Febrero 2026", "Enero 2026"])
  })

  it("cada cambio dice de cuánto a cuánto", () => {
    expect(cambios[0].desde).toBe("$100.000")
    expect(cambios[0].hasta).toBe("$120.000")
  })

  it("el más viejo no tiene 'desde': no hay mes anterior", () => {
    expect(cambios[cambios.length - 1].desde).toBeNull()
    expect(cambios[cambios.length - 1].hasta).toBe("$80.000")
  })

  it("🔴 compara el BRUTO, no el neto", () => {
    // Mismo bruto, neto distinto (cambió una retención): no es un aumento y no debe figurar.
    const serie = [mes(2026, 2, 100_000, 70_000), mes(2026, 1, 100_000, 80_000)]
    expect(cambiosSalariales(serie)).toHaveLength(1)
  })

  it("el neto viaja igual, como detalle", () => {
    expect(cambios[0].detalle).toBe("neto $96.000")
  })

  it("una serie vacía no rompe", () => {
    expect(cambiosSalariales([])).toEqual([])
  })
})

describe("resumenSerie — el colapso se declara, no se esconde", () => {
  it("dice cuántos períodos hay y cuántos fueron cambio", () => {
    expect(resumenSerie(SERIE, 3)).toBe("5 períodos cargados · 3 con cambio de bruto")
  })

  it("si todos fueron cambio no repite el número", () => {
    expect(resumenSerie(SERIE.slice(0, 3), 3)).toBe("3 períodos cargados")
  })

  it("sin serie no dice nada", () => {
    expect(resumenSerie([], 0)).toBe("")
  })
})
