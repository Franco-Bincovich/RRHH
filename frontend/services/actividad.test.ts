import { describe, expect, it } from "vitest"

import {
  AVISO_ANTES_MS,
  INACTIVIDAD_MAXIMA_MS,
  debeAvisar,
  minutosRestantes,
} from "@/services/actividad"

/**
 * El aviso previo al corte por inactividad. Es UX: el corte lo hace el backend.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * Se prueban las funciones puras y no el componente: sin jsdom no corre el `useEffect` ni el
 * intervalo, así que un test de render mostraría el banner oculto en los dos casos. Cada test
 * pasa un tiempo transcurrido DISTINTO a un lado y otro de los dos bordes (7h45 y 8h), así que
 * ni `true` ni `false` constantes sobreviven, y correr el umbral rompe el borde de abajo.
 */
const MINUTO = 60_000
const HORA = 60 * MINUTO

describe("debeAvisar", () => {
  it("no avisa durante el uso normal", () => {
    expect(debeAvisar(2 * HORA)).toBe(false)
  })

  it("no avisa un minuto antes del umbral", () => {
    expect(debeAvisar(INACTIVIDAD_MAXIMA_MS - AVISO_ANTES_MS - MINUTO)).toBe(false)
  })

  it("avisa desde las 7h45", () => {
    expect(debeAvisar(INACTIVIDAD_MAXIMA_MS - AVISO_ANTES_MS)).toBe(true)
  })

  it("sigue avisando a falta de un minuto", () => {
    expect(debeAvisar(INACTIVIDAD_MAXIMA_MS - MINUTO)).toBe(true)
  })

  it("deja de avisar pasado el corte: ahí el 401 manda al login solo", () => {
    // Un banner que diga "te quedan -3 minutos" no ayuda a nadie.
    expect(debeAvisar(INACTIVIDAD_MAXIMA_MS + MINUTO)).toBe(false)
  })
})

describe("minutosRestantes", () => {
  it("cuenta los que faltan", () => {
    expect(minutosRestantes(INACTIVIDAD_MAXIMA_MS - 10 * MINUTO)).toBe(10)
  })

  it("nunca muestra cero ni negativos", () => {
    expect(minutosRestantes(INACTIVIDAD_MAXIMA_MS)).toBe(1)
  })

  it("redondea hacia arriba: 'en 1 minuto' y no 'en 0'", () => {
    expect(minutosRestantes(INACTIVIDAD_MAXIMA_MS - 30_000)).toBe(1)
  })
})

describe("el umbral del front coincide con el del backend", () => {
  it("8 horas, el mismo número que utils/_sesion_inactividad.py", () => {
    // Si allá cambia y acá no, el aviso miente: aparecería tarde o no aparecería.
    expect(INACTIVIDAD_MAXIMA_MS).toBe(8 * HORA)
  })
})
