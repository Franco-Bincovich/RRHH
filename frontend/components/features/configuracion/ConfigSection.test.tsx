import { renderToStaticMarkup } from "react-dom/server"
import { Accordion } from "@base-ui/react/accordion"
import { describe, expect, it } from "vitest"

import { ConfigSection } from "./ConfigSection"

/**
 * ConfigSection es la ÚNICA shell plegable del sistema: la usan /configuracion y las tres
 * cards del dashboard que listan cosas que crecen sin techo. Lo que se verifica acá es el
 * mecanismo —qué se ve plegada y qué desplegada— una sola vez, en el componente compartido.
 * Plegada: título + badge y nada más. Desplegada: eso, más el panel.
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

function render(abierta: boolean): string {
  return renderToStaticMarkup(
    <Accordion.Root defaultValue={abierta ? ["s"] : []}>
      <ConfigSection value="s" title="Una sección" badge={<span>7</span>}>
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

describe("plegada no asoma nada del contenido", () => {
  /**
   * Es la propiedad que define a esta shell y la razón por la que se sacó el prop `preview`:
   * plegada tiene que medir SIEMPRE lo mismo, sea cual sea el largo de lo que esconde. Si
   * volviera a haber una forma de dejar filas asomando, la card plegada volvería a ocupar casi
   * lo que ocupa abierta y el acordeón dejaría de servir para lo único que sirve.
   *
   * Se afirma sobre el markup entero, no sobre un slot: así cubre también a un `preview` nuevo
   * que alguien agregue con otro nombre.
   */
  it("lo único que sale además del título es el badge", () => {
    const plegada = render(false)
    expect(plegada).toContain("Una sección")
    expect(plegada).toContain("7")
    expect(plegada).not.toContain(CONTENIDO)
  })
})
