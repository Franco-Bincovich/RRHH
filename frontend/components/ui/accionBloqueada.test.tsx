/**
 * `AccionBloqueada`: una acción que hoy no se puede hacer, con el motivo A LA VISTA.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 * El componente se RENDERIZA de verdad (`renderToStaticMarkup`), no se lee su fuente: lo que se
 * afirma es que el motivo SALE EN EL MARKUP, que es lo único que el usuario ve. Un test que
 * mirara el texto del archivo pasaría aunque el `{motivo && …}` estuviera borrado.
 *
 * El caso que más importa es el segundo: sin motivo, el componente tiene que ser TRANSPARENTE.
 * Si dibujara algo igual —una caja vacía, un margen— ensuciaría las cuatro pantallas que lo usan
 * en su estado normal, que es el 99% del tiempo.
 */
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { AccionBloqueada } from "@/components/ui/AccionBloqueada"
import { MOTIVO_SIN_EMPRESA } from "@/hooks/useEmpresaConcreta"

function render(motivo: string | null): string {
  return renderToStaticMarkup(
    <AccionBloqueada motivo={motivo}>
      {(bloqueada) => (
        <button type="button" disabled={bloqueada}>
          Guardar
        </button>
      )}
    </AccionBloqueada>,
  )
}

describe("el motivo se ve, no se adivina", () => {
  it("con motivo, el texto está en la pantalla y el control queda deshabilitado", () => {
    const html = render(MOTIVO_SIN_EMPRESA)
    // El TEXTO, no un tooltip: es lo único que existe en touch y con teclado.
    expect(html).toContain("Elegí una empresa en el selector")
    expect(html).toContain("disabled")
  })

  it("el motivo va ADEMÁS como title, y sobre el wrapper", () => {
    /**
     * 🔴 SOBRE EL WRAPPER Y NO SOBRE EL BOTÓN: un `<button disabled>` no dispara eventos de
     * mouse en varios navegadores, así que su propio `title` no llega a mostrarse nunca. El
     * test lo fija mirando que el atributo esté en un elemento que NO es el botón.
     */
    const html = render("porque sí, con razón suficiente")
    expect(html).toContain('title="porque sí, con razón suficiente"')
    expect(html).not.toContain('<button type="button" disabled="" title=')
  })

  it("sin motivo no dibuja nada extra: el control sale habilitado y solo", () => {
    const html = render(null)
    expect(html).not.toContain("disabled")
    expect(html).not.toContain("title=")
    // Ni la nota ni su ícono: el estado normal de las cuatro pantallas que lo usan.
    expect(html).not.toContain("svg")
  })
})
