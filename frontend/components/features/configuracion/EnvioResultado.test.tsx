import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { EnvioResultado, TITULO_COMPLETO, TITULO_INCOMPLETO } from "./EnvioResultado"
import type { EnvioResponse } from "@/types/plantillas"

/**
 * El resumen de un envío. La propiedad que se cuida acá es UNA: **un lote incompleto no se puede
 * ver como un éxito completo.**
 *
 * El backend manda de a uno con presupuesto de tiempo y devuelve cinco números. Un "Enviado" a
 * secas sobre un 200 que en realidad dice "salieron 30 de 50" deja a RRHH creyendo que el
 * comunicado llegó a todos, y la única forma de enterarse sería que alguien de afuera reclame.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. Los casos recorren los DOS desenlaces del mismo eje: completo y cada forma de incompleto
 *    (parcial por tiempo, y con fallidos). Con solo el caso feliz, un componente que dijera
 *    siempre "Listo" pasaría; con solo el parcial, uno que dijera siempre "no salió completo"
 *    también — y ese es igual de malo, porque enseña a ignorar el aviso.
 * 2. Los títulos se importan del propio componente (`TITULO_COMPLETO` / `TITULO_INCOMPLETO`) en
 *    vez de copiarse como literales: si alguien los edita, el test sigue afirmando la DISTINCIÓN
 *    y no el texto viejo. Lo que no puede pasar sin romper es que los dos se vuelvan el mismo,
 *    que es la regresión real (hay un caso que lo afirma explícito).
 * 3. GUARDA DE MARKUP en `render()`: si el componente no montara, la salida sería "" y todos los
 *    `not.toContain` pasarían sin haber mirado nada.
 * 4. `omitidos` se prueba SIN parcial ni fallidos, para fijar que NO cuenta como problema: es la
 *    idempotencia del backend (ya se les había mandado hoy). Un componente que lo tratara como
 *    error diría "no salió completo" sobre un reintento perfecto y rojea acá.
 */

const VACIO: EnvioResponse = {
  enviados: 0, omitidos: 0, fallidos: [], parcial: false, sin_procesar: 0, segundos: 2.5,
}

function render(extra: Partial<EnvioResponse> = {}): string {
  const html = renderToStaticMarkup(<EnvioResultado res={{ ...VACIO, ...extra }} />)
  expect(html.length, "el resumen no renderizó nada: toda aserción de abajo sería vacua")
    .toBeGreaterThan(0)
  return html
}

describe("un lote incompleto NO se muestra como éxito", () => {
  it("🔴 cortado por tiempo: el título avisa y dice cuántos quedaron", () => {
    const html = render({ enviados: 30, parcial: true, sin_procesar: 20 })

    expect(html).toContain(TITULO_INCOMPLETO)
    expect(html).not.toContain(TITULO_COMPLETO)
    expect(html).toContain("30")     // los que sí salieron
    expect(html).toContain("20")     // los que quedaron sin procesar
    expect(html).toContain("sin procesar")
  })

  it("🔴 con fallidos: el título avisa y se lee QUIÉN y POR QUÉ", () => {
    const html = render({
      enviados: 2,
      fallidos: [{ destinatario: "ana@k.com", motivo: "el empleado no tiene email corporativo cargado" }],
    })

    expect(html).toContain(TITULO_INCOMPLETO)
    expect(html).not.toContain(TITULO_COMPLETO)
    expect(html).toContain("ana@k.com")
    expect(html).toContain("no tiene email corporativo")
  })

  it("dice qué hacer con lo que quedó, y que no le va a llegar dos veces a nadie", () => {
    // Sin esta línea, un usuario prudente no reintenta por miedo a duplicar — y los 20 que
    // faltan no reciben nunca el mail.
    const html = render({ enviados: 30, parcial: true, sin_procesar: 20 })
    expect(html).toContain("dos veces")
  })

  it("los dos títulos son textos DISTINTOS (si se igualaran, todo lo de arriba sería vacuo)", () => {
    expect(TITULO_COMPLETO).not.toBe(TITULO_INCOMPLETO)
  })
})

describe("un lote completo sí se muestra como completo", () => {
  it("🔴 sin parcial ni fallidos, el título es el de éxito", () => {
    const html = render({ enviados: 5 })

    expect(html).toContain(TITULO_COMPLETO)
    expect(html).not.toContain(TITULO_INCOMPLETO)
    expect(html).toContain("5")
  })

  it("no aparece ninguna línea de fallos ni de corte", () => {
    const html = render({ enviados: 5 })
    expect(html).not.toContain("sin procesar")
    expect(html).not.toContain("no se pudieron enviar")
  })
})

describe("omitidos no es un problema: es la idempotencia", () => {
  it("🔴 con omitidos y nada más, el lote sigue siendo COMPLETO", () => {
    const html = render({ enviados: 3, omitidos: 7 })

    expect(html).toContain(TITULO_COMPLETO)
    expect(html).not.toContain(TITULO_INCOMPLETO)
  })

  it("y se explica por qué no se les volvió a mandar, sin la palabra «omitidos»", () => {
    const html = render({ enviados: 3, omitidos: 7 })

    expect(html).toContain("7")
    expect(html).toContain("ya se le había mandado este mail hoy")
    expect(html).not.toContain("omitidos")   // jerga del contrato, no del usuario
  })

  it("con cero omitidos la línea no aparece (una lista de ceros deja de leerse)", () => {
    expect(render({ enviados: 3 })).not.toContain("ya se le había mandado")
  })
})

describe("los cinco números están todos representados", () => {
  it("un lote con las cuatro cosas a la vez las muestra todas", () => {
    const html = render({
      enviados: 30, omitidos: 5, parcial: true, sin_procesar: 13,
      fallidos: [{ destinatario: "beto@k.com", motivo: "MAIL_ERROR_PROVEEDOR: rechazado" }],
    })

    expect(html).toContain("30")
    expect(html).toContain("5")
    expect(html).toContain("13")
    expect(html).toContain("beto@k.com")
    expect(html).toContain(TITULO_INCOMPLETO)
  })
})
