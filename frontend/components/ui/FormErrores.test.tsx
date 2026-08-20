import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { FormErrores } from "@/components/ui/FormErrores"

/**
 * El banner de resumen del patrón de modal de formulario. Render a string: el proyecto corre
 * vitest sin jsdom.
 */
describe("FormErrores", () => {
  it("dice la cuenta exacta", () => {
    expect(renderToStaticMarkup(<FormErrores cantidad={2} />)).toContain("Revisá 2 campos")
  })

  it("con uno solo va en singular", () => {
    const html = renderToStaticMarkup(<FormErrores cantidad={1} />)
    expect(html).toContain("Revisá 1 campo")
    expect(html).not.toContain("1 campos")
  })

  it("sin errores no se renderiza: no es un banner vacío ni un espacio reservado", () => {
    expect(renderToStaticMarkup(<FormErrores cantidad={0} />)).toBe("")
  })

  it("se anuncia solo al lector de pantalla", () => {
    // Aparece después de apretar Guardar, cuando el foco está en el botón: sin `role="alert"`
    // quien no ve la pantalla no se entera de que el envío se frenó.
    expect(renderToStaticMarkup(<FormErrores cantidad={3} />)).toContain('role="alert"')
  })
})
