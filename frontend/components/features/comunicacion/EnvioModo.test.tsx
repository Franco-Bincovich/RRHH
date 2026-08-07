import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { EnvioModo } from "./EnvioModo"
import { MOTIVO_VARIABLES } from "./direccionesLibres"

/**
 * 🔴 UNA PLANTILLA CON VARIABLES DESHABILITA EL MODO LIBRE **ANTES**, con el motivo a la vista.
 *
 * No es un detalle de estilo. Para cuando un error post-envío llega, el usuario ya escribió las
 * direcciones, ya confirmó y ya cree que el mail salió. Y el mail que se evita es peor que el
 * error: llega a alguien de afuera con `{{nombre_empleado}}` sin resolver y no se deshace.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. LOS DOS VALORES DE `usaVariables` se recorren. Con solo `true`, un componente que
 *    deshabilitara el modo libre SIEMPRE pasaría — y eso deja la feature entera muerta, que es
 *    peor que el bug. Con solo `false`, la barrera se podría borrar sin que nada rojee.
 * 2. El estado del botón se mira por el ATRIBUTO `disabled=""`, NUNCA por la palabra "disabled":
 *    la clase de este botón incluye `disabled:...` de Tailwind y `toContain("disabled")` daría
 *    verde con el botón HABILITADO. Es el falso positivo que este repo ya se comió una vez.
 * 3. GUARDA DE MARKUP: si el componente no montara, la salida sería "" y todos los `not.toContain`
 *    pasarían sin haber mirado nada.
 * 4. El motivo se importa de `direccionesLibres` en vez de copiarse: si alguien edita el texto,
 *    el test sigue afirmando que ESE motivo se muestra, no una versión vieja.
 *
 * ⚠️ SIN RED, explícito: el CLIC en el botón. vitest corre sin jsdom, así que se verifica el
 * markup —qué botón está deshabilitado y qué dice el cartel—, no que `onCambio` se dispare.
 */

function render(usaVariables: boolean, modo: "empleados" | "libre" = "empleados"): string {
  const html = renderToStaticMarkup(
    <EnvioModo modo={modo} usaVariables={usaVariables} onCambio={() => {}} />,
  )
  expect(html.length, "el selector no renderizó nada: toda aserción de abajo sería vacua")
    .toBeGreaterThan(0)
  return html
}

/** El `<button>` que contiene ese texto, o null. */
function boton(html: string, texto: string): string | null {
  for (const m of html.matchAll(/<button[^>]*>[\s\S]*?<\/button>/g)) {
    if (m[0].includes(texto)) return m[0]
  }
  return null
}

/** ¿Ese botón está deshabilitado? Por el ATRIBUTO — ver el punto 2 del encabezado. */
function deshabilitado(html: string, texto: string): boolean {
  const b = boton(html, texto)
  expect(b, `no se encontró el botón "${texto}"`).not.toBeNull()
  return b!.includes('disabled=""')
}

describe("con una plantilla que usa variables", () => {
  it("🔴 el modo de direcciones sueltas está DESHABILITADO", () => {
    expect(deshabilitado(render(true), "Escribir direcciones")).toBe(true)
  })

  it("🔴 y el motivo se lee, sin jerga: dice que usa datos del empleado", () => {
    const html = render(true)

    expect(html).toContain(MOTIVO_VARIABLES)
    expect(html).toContain("solo se puede enviar a empleados")
    expect(html).not.toContain("{{")   // no se le muestra la sintaxis interna al usuario
  })

  it("el modo de empleados SIGUE habilitado: es el que sí resuelve las variables", () => {
    expect(deshabilitado(render(true), "Empleados del sistema")).toBe(false)
  })
})

describe("con una plantilla sin variables", () => {
  it("🔴 el modo de direcciones sueltas está habilitado", () => {
    // Sin este caso, el test de arriba pasaría con el botón deshabilitado para siempre.
    expect(deshabilitado(render(false), "Escribir direcciones")).toBe(false)
  })

  it("y el cartel NO aparece", () => {
    expect(render(false)).not.toContain(MOTIVO_VARIABLES)
  })

  it("los dos modos se ofrecen", () => {
    const html = render(false)
    expect(boton(html, "Empleados del sistema")).not.toBeNull()
    expect(boton(html, "Escribir direcciones")).not.toBeNull()
  })
})

describe("el modo activo se marca", () => {
  it("empleados", () => {
    expect(boton(render(false, "empleados"), "Empleados del sistema")).toContain('aria-pressed="true"')
  })

  it("libre", () => {
    expect(boton(render(false, "libre"), "Escribir direcciones")).toContain('aria-pressed="true"')
  })

  it("y solo uno a la vez (si no, no habría forma de saber qué se va a mandar)", () => {
    const html = render(false, "libre")
    expect(boton(html, "Empleados del sistema")).toContain('aria-pressed="false"')
  })
})
