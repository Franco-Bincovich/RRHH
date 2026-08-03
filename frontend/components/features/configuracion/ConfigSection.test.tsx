import { renderToStaticMarkup } from "react-dom/server"
import { Accordion } from "@base-ui/react/accordion"
import { describe, expect, it } from "vitest"

import { ConfigSection } from "./ConfigSection"

/**
 * ConfigSection es la ÚNICA shell plegable del sistema: la usan /configuracion y las tres
 * cards del dashboard que listan cosas que crecen sin techo. Lo que se verifica acá es el
 * mecanismo —qué se ve plegada y qué desplegada— una sola vez, en el componente compartido.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * NO se falsea el acordeón: corre el <Accordion.Root> real de base-ui, y lo único que cambia
 * entre un caso y otro es su `defaultValue`. Con un acordeón mockeado que renderice siempre
 * sus children, "plegada" y "desplegada" darían el MISMO markup y el test pasaría con el
 * plegado roto — que es justo lo que viene a cubrir. Por eso el caso "plegada" afirma que el
 * contenido NO está: si base-ui pasara a montar el panel cerrado (keepMounted), rojea acá y
 * no en producción.
 *
 * vitest corre sin jsdom, así que no hay click: el eje abierto/cerrado se recorre por el
 * estado inicial del Root, no por interacción. La operabilidad con teclado no se testea acá
 * porque no es nuestra: el trigger de base-ui ES un <button>, y eso lo garantiza el DOM.
 */

const CONTENIDO = "contenido-del-panel"
const PREVIEW = "contenido-del-preview"

function render(abierta: boolean, props: { preview?: string; disabled?: boolean } = {}): string {
  return renderToStaticMarkup(
    <Accordion.Root defaultValue={abierta ? ["s"] : []}>
      <ConfigSection
        value="s"
        title="Una sección"
        preview={props.preview ? <p>{props.preview}</p> : undefined}
        disabled={props.disabled}
      >
        <p>{CONTENIDO}</p>
      </ConfigSection>
    </Accordion.Root>,
  )
}

describe("desplegar y colapsar", () => {
  it("plegada esconde el contenido del panel", () => {
    expect(render(false)).not.toContain(CONTENIDO)
  })

  it("desplegada lo muestra", () => {
    expect(render(true)).toContain(CONTENIDO)
  })

  it("el título se ve en los dos estados — es el trigger, no parte del panel", () => {
    expect(render(false)).toContain("Una sección")
    expect(render(true)).toContain("Una sección")
  })
})

describe("preview — lo que se ve siempre", () => {
  it("está plegada y desplegada; solo la cola aparece y desaparece", () => {
    const plegada = render(false, { preview: PREVIEW })
    const abierta = render(true, { preview: PREVIEW })
    expect(plegada).toContain(PREVIEW)
    expect(plegada).not.toContain(CONTENIDO)
    expect(abierta).toContain(PREVIEW)
    expect(abierta).toContain(CONTENIDO)
  })
})

describe("disabled — sin nada que plegar", () => {
  // El chevron promete que hay algo atrás. Si no lo hay, no va: se identifica por la clase
  // que le pone la rotación, que es propia de ese icono y de ningún otro de la shell.
  const chevron = (html: string) => html.includes("group-data-panel-open:rotate-180")

  it("sin disabled hay chevron", () => {
    expect(chevron(render(false))).toBe(true)
  })

  it("con disabled no hay chevron", () => {
    expect(chevron(render(false, { disabled: true }))).toBe(false)
  })

  it("el trigger queda inoperable, no solo sin flechita", () => {
    // Si solo se escondiera el chevron, el <button> seguiría plegando al Enter y la card
    // se cerraría sin manera visible de volver a abrirla.
    expect(render(false, { disabled: true })).toContain("disabled=\"\"")
  })
})
