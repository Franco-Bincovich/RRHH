import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { AVISO_IRREVERSIBLE, EnvioPie } from "./EnvioPie"

/**
 * El pie del modal de envío: quién puede apretar, cuándo, y qué se le dice antes.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. NO se mockea nada: `EnvioPie` recibe todo por PROP y se renderiza el componente real. Un
 *    mock de `getEmpresaActivaId` acá no se ejecutaría nunca y el encabezado estaría mintiendo
 *    (ya pasó en la primera versión de PlantillaAcciones.test.tsx).
 * 2. Cada eje se recorre en sus DOS valores. "El botón está deshabilitado con cero" pasaría con
 *    el botón deshabilitado SIEMPRE, que dejaría la pantalla inservible; por eso hay un caso con
 *    cantidad > 0 que afirma lo contrario.
 * 3. El estado del botón se mira por el ATRIBUTO `disabled=""`, NUNCA por la palabra "disabled":
 *    la clase de `<Button>` incluye siempre `disabled:pointer-events-none` y `disabled:opacity-50`,
 *    así que `toContain("disabled")` da verde con el botón HABILITADO. Es el falso positivo que
 *    entra por la puerta de Tailwind y que este repo ya se comió una vez.
 * 4. GUARDA DE MARKUP: `render()` afirma que la salida no está vacía antes de cualquier otra
 *    aserción. Sin ella, un componente que no monte (o que se renderice dentro de un acordeón
 *    plegado, o del portal de un Dialog) devolvería "" y TODOS los `not.toContain` pasarían sin
 *    haber mirado nada.
 */

const BASE = {
  cantidad: 3, confirmando: false, enviando: false, sinEmpresa: false,
  onPedirConfirmacion: () => {}, onVolver: () => {}, onEnviar: () => {}, onCancelar: () => {},
}

function render(extra: Partial<typeof BASE> = {}): string {
  const html = renderToStaticMarkup(<EnvioPie {...BASE} {...extra} />)
  expect(html.length, "el pie no renderizó nada: toda aserción de abajo sería vacua").toBeGreaterThan(0)
  return html
}

/** El `<button>` que contiene ese texto, o null. */
function boton(html: string, texto: string): string | null {
  for (const m of html.matchAll(/<button[^>]*>[\s\S]*?<\/button>/g)) {
    if (m[0].includes(texto)) return m[0]
  }
  return null
}

/** ¿Ese botón está deshabilitado? Por el ATRIBUTO — ver el punto 3 del encabezado. */
function deshabilitado(html: string, texto: string): boolean {
  const b = boton(html, texto)
  expect(b, `no se encontró el botón "${texto}"`).not.toBeNull()
  return b!.includes('disabled=""')
}

describe("con cero seleccionados no se puede avanzar", () => {
  it("🔴 el botón de enviar está deshabilitado", () => {
    expect(deshabilitado(render({ cantidad: 0 }), "Enviar (0)")).toBe(true)
  })

  it("con al menos uno, se habilita (si no, el test de arriba pasaría con el botón muerto)", () => {
    expect(deshabilitado(render({ cantidad: 1 }), "Enviar (1)")).toBe(false)
  })

  it("y en el paso de confirmación, cero tampoco deja apretar", () => {
    expect(deshabilitado(render({ cantidad: 0, confirmando: true }), "Sí, enviar")).toBe(true)
  })
})

describe("la confirmación dice el número, y dice que no se deshace", () => {
  it("🔴 el primer paso NO manda: ofrece confirmar", () => {
    const html = render({ cantidad: 3 })
    expect(boton(html, "Enviar (3)")).not.toBeNull()
    // Sin este par, un rediseño que sacara el paso de confirmación pasaría desapercibido.
    expect(boton(html, "Sí, enviar")).toBeNull()
    expect(html).not.toContain(AVISO_IRREVERSIBLE)
  })

  it("🔴 el segundo paso dice a cuántas personas y que es irreversible", () => {
    const html = render({ cantidad: 17, confirmando: true })
    expect(html).toContain("17")
    expect(html).toContain("personas")
    expect(html).toContain(AVISO_IRREVERSIBLE)
    expect(boton(html, "Sí, enviar")).not.toBeNull()
  })

  it("con una sola persona el texto no dice «1 personas»", () => {
    const html = render({ cantidad: 1, confirmando: true })
    expect(html).toContain("persona.")
    expect(html).not.toContain("personas")
  })

  it("se puede volver atrás sin mandar", () => {
    expect(boton(render({ confirmando: true }), "Volver")).not.toBeNull()
  })
})

describe("mientras manda, se ve que está mandando", () => {
  it("🔴 el botón cambia de texto: el lote puede tardar hasta dos minutos", () => {
    const html = render({ confirmando: true, enviando: true })
    expect(html).toContain("Enviando")
    expect(boton(html, "Sí, enviar")).toBeNull()
  })

  it("y no se puede apretar de nuevo (un segundo lote sería un segundo mail para todos)", () => {
    expect(deshabilitado(render({ confirmando: true, enviando: true }), "Enviando")).toBe(true)
  })

  it("volver atrás también se bloquea mientras el pedido está en vuelo", () => {
    expect(deshabilitado(render({ confirmando: true, enviando: true }), "Volver")).toBe(true)
  })
})

describe("en modo consolidado no se envía", () => {
  /**
   * El backend resuelve la plantilla con la empresa del request: sin empresa solo encuentra la
   * GLOBAL, así que el mail saldría con un texto distinto del que se ve en pantalla y sin ningún
   * error. Para una acción irreversible, ese es el peor desenlace posible.
   */
  it("🔴 no hay ningún botón de envío, ni siquiera deshabilitado", () => {
    const html = render({ sinEmpresa: true, cantidad: 3 })
    expect(boton(html, "Enviar (3)")).toBeNull()
    expect(boton(html, "Sí, enviar")).toBeNull()
  })

  it("y el motivo se lee, sin jerga de backend", () => {
    const html = render({ sinEmpresa: true })
    expect(html).toContain("elegí una empresa en el selector")
    expect(html).not.toContain("empresa_id")
  })
})
