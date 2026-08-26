import { describe, expect, it } from "vitest"

import { RUTAS_OCULTAS } from "@/components/layout/nav-config"
import type { AlertaDashboard } from "@/services/dashboard"
import { DESTINOS } from "./_destinosKpi"
import { alertasVisibles, kpiOculto } from "./_ocultoEnDashboard"

/**
 * Lo que el dashboard esconde porque su sección salió del menú.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. 🔴 **Que el ocultamiento NO se derivara de `RUTAS_OCULTAS`.** Es la única aserción que
 *    importa acá y por eso ninguno de los casos escribe `"Masa salarial del mes"` como constante
 *    de entrada: los títulos y los href se DERIVAN del mapa real y de la lista real. Con una
 *    lista propia acá, un flag suelto en `_ocultoEnDashboard` pasaría los tests igual — y el día
 *    que Franco reponga Costos habría dos interruptores, uno de ellos invisible.
 * 2. **Hay una CONTRACARA por cada caso**: una card que NO está oculta, una alerta que NO se
 *    filtra y una alerta sin href. Sin ellas, un `kpiOculto` que devolviera `true` siempre —o un
 *    `alertasVisibles` que devolviera `[]`— pasaría la mitad de este archivo.
 */

/** Un alerta cualquiera; lo único que se mira es el href. */
const alerta = (href: string | null): AlertaDashboard =>
  ({ tipo: "x", mensaje: "m", nivel: "warning", href })

/** Los títulos cuyo destino cayó en `RUTAS_OCULTAS`. Se DERIVA: el día que Costos vuelva al
 *  menú esto queda vacío y la guarda de abajo lo dice, en vez de que el archivo pase en el aire. */
const OCULTOS = Object.keys(DESTINOS)
  .filter((t) => RUTAS_OCULTAS.includes(DESTINOS[t].split("?")[0]))

describe("kpiOculto: una card cuya sección salió del menú no se pinta", () => {
  it("guarda: hay al menos una card oculta y al menos una visible", () => {
    // Sin la primera, los `forEach` de abajo no miran nada. Sin la segunda, `kpiOculto` podría
    // ser `() => true` y este archivo entero seguiría en verde.
    expect(OCULTOS.length).toBeGreaterThanOrEqual(1)
    expect(Object.keys(DESTINOS).length - OCULTOS.length).toBeGreaterThanOrEqual(5)
  })

  it("las que apuntan a una ruta oculta dan true", () => {
    OCULTOS.forEach((t) => expect(kpiOculto(t), t).toBe(true))
  })

  it("EL CONTRASTE: las demás dan false", () => {
    Object.keys(DESTINOS)
      .filter((t) => !OCULTOS.includes(t))
      .forEach((t) => expect(kpiOculto(t), t).toBe(false))
  })

  it("una card sin destino declarado NO queda oculta por accidente", () => {
    // "Headcount por empresa" vive en SIN_DESTINO: no apunta a ninguna sección, así que ninguna
    // ruta oculta la puede alcanzar. Un `kpiOculto` que devolviera true ante `undefined` la
    // borraría de la pantalla sin que nadie lo hubiera decidido.
    expect(kpiOculto("Headcount por empresa")).toBe(false)
    expect(kpiOculto("un título que no existe")).toBe(false)
  })
})

describe("alertasVisibles: una alerta que empuja a una pantalla escondida no se muestra", () => {
  it("cae la que linkea a una ruta oculta", () => {
    const ocultas = RUTAS_OCULTAS.map(alerta)
    expect(ocultas.length).toBeGreaterThanOrEqual(1)   // guarda
    expect(alertasVisibles(ocultas)).toEqual([])
  })

  it("EL CONTRASTE: la que linkea a una ruta viva sobrevive", () => {
    const viva = alerta("/inventario")
    expect(RUTAS_OCULTAS).not.toContain("/inventario")  // si algún día se oculta, este test lo dice
    expect(alertasVisibles([viva])).toEqual([viva])
  })

  it("y una alerta SIN href se muestra siempre: no empuja a ninguna parte", () => {
    const sinLink = alerta(null)
    expect(alertasVisibles([sinLink])).toEqual([sinLink])
  })

  it("el filtro mira el camino, no la querystring", () => {
    // Los href de las alertas agregadas llevan filtros (`/empleados?estado=activo&...`). Sin
    // cortar la query, una ruta oculta con filtro se colaría — es el mismo corte que hace
    // `destino()` antes de preguntar por el permiso.
    const conQuery = alerta(`${RUTAS_OCULTAS[0]}?anio=2026`)
    expect(alertasVisibles([conQuery])).toEqual([])
  })
})
