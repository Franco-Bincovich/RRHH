import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { SaldoResumen } from "./SaldoResumen"
import type { SaldoVacaciones } from "@/types/vacaciones"

/**
 * ⚠️ vitest corre con environment "node" y SIN jsdom: esto verifica el MARKUP, no la
 * interacción, y `useEffect` no se ejecuta. Acá eso NO es una limitación disimulada:
 * `SaldoResumen` es puramente presentacional —recibe el saldo ya calculado y no fetchea
 * nada—, así que el markup ES todo su comportamiento. (Distinto del caso #4 del manual,
 * donde un test así dejaba pasar un guard borrado porque el guard vivía en un useEffect.)
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 * El saldo entra como prop, así que cada test construye el estado exacto que quiere probar:
 * un período por vencer, uno ya vencido, uno agotado. Si el componente dejara de renderizar
 * el desglose —o volviera a mostrar solo los cuatro totales, que es la regresión que
 * importa— el string no contendría el año ni la fecha de vencimiento y el test falla.
 */

const BASE: SaldoVacaciones = {
  empleado_id: "e1",
  asignados: 35,
  gozados: 0,
  pedidos: 0,
  disponibles: 35,
  vencidos: 0,
  por_periodo: [
    { periodo: 2022, cupo: 14, gozados: 0, pedidos: 0, disponibles: 14, vence: "2026-12-31", vencido: false },
    { periodo: 2023, cupo: 21, gozados: 0, pedidos: 0, disponibles: 21, vence: "2027-12-31", vencido: false },
  ],
}

const render = (saldo: SaldoVacaciones, dias?: number) =>
  renderToStaticMarkup(<SaldoResumen saldo={saldo} tipo="vacaciones" diasSolicitados={dias} />)

describe("SaldoResumen", () => {
  it("muestra el desglose por período con su fecha de vencimiento", () => {
    const html = render(BASE)
    expect(html).toContain("Por período")
    expect(html).toContain("2022")
    expect(html).toContain("31/12/2026")
    expect(html).toContain("2023")
    expect(html).toContain("31/12/2027")
  })

  it("señala cuál es el más antiguo, que es el que hay que gastar primero", () => {
    // Sin este aviso el usuario ve dos números y no sabe cuál se le va a caer.
    expect(render(BASE)).toContain("período 2022")
  })

  it("formatea la fecha sin construir un Date", () => {
    // `new Date("2026-12-31")` se parsea en UTC y en Argentina (UTC-3) muestra el 30/12.
    expect(render(BASE)).not.toContain("30/12/2026")
  })

  it("avisa de los días ya vencidos y aclara que no cuentan", () => {
    const html = render({ ...BASE, vencidos: 9 })
    expect(html).toContain("vencieron 9")
    expect(html).toContain("No se cuentan")
  })

  it("no lista los períodos vencidos ni los agotados como saldo utilizable", () => {
    const html = render({
      ...BASE,
      por_periodo: [
        { periodo: 2019, cupo: 14, gozados: 0, pedidos: 0, disponibles: 14, vence: "2023-12-31", vencido: true },
        { periodo: 2024, cupo: 21, gozados: 21, pedidos: 0, disponibles: 0, vence: "2028-12-31", vencido: false },
      ],
    })
    expect(html).not.toContain("Por período")
    expect(html).not.toContain("31/12/2023")
  })

  it("sigue avisando cuando lo solicitado supera lo disponible", () => {
    expect(render({ ...BASE, disponibles: 3 }, 5)).toContain("superan el saldo disponible")
  })

  it("no rompe si el backend no manda el desglose", () => {
    // Contrato viejo: `por_periodo` ausente. Los cuatro totales tienen que seguir saliendo.
    const viejo = { ...BASE, por_periodo: undefined } as unknown as SaldoVacaciones
    const html = render(viejo)
    expect(html).toContain("Disponibles")
    expect(html).not.toContain("Por período")
  })
})
