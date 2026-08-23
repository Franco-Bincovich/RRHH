import { readFileSync } from "node:fs"
import { join } from "node:path"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import type { OpcionVista } from "./_catalogosObjetivos"
import { TipoObjetivoTabs } from "./TipoObjetivoTabs"

/**
 * El selector de las dos vistas de objetivos.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. 🔴 **Las etiquetas del fixture NO son "Anual" y "Operativo".** Son dos palabras que no
 *    aparecen en ningún lado del código. Con las de verdad, un componente que se las hubiera
 *    hardcodeado —que es exactamente lo que el endpoint `/campos` existe para impedir— pasaría
 *    todos los tests de render. Con éstas, sólo pasa si de verdad las está leyendo del catálogo.
 * 2. **El `value` sí es el literal real** (`anual`/`operativo`): ése no se inventa, es el del
 *    CHECK de la base y es lo que viaja en la URL.
 * 3. **Se afirma el `value` vacío de "Todas" por separado.** Un componente que mandara
 *    `value="todas"` renderizaría igual de bien y traería CERO filas del backend.
 * 4. El caso de catálogo vacío lleva su contraste con catálogo lleno; sin él, un componente que
 *    devolviera `null` siempre pasaría la mitad del archivo.
 *
 * ⚠️ vitest corre con `environment: "node"` y sin jsdom: se verifica el MARKUP, no el click. Que
 * este componente sea afirmable así es la razón por la que el fetch del catálogo vive en
 * `_catalogosObjetivos` y no acá adentro — con el `useEffect` propio, lo único que un test vería
 * sería el estado de carga.
 */

const VISTAS: OpcionVista[] = [
  { value: "anual", label: "Del directorio" },
  { value: "operativo", label: "Del día a día" },
]

const render = (vistas: OpcionVista[], valor: "" | "anual" | "operativo" = "") =>
  renderToStaticMarkup(<TipoObjetivoTabs vistas={vistas} valor={valor} onCambio={() => {}} />)

describe("las etiquetas las trae el backend", () => {
  it("dibuja una solapa por vista, con la etiqueta que vino en el catálogo", () => {
    const html = render(VISTAS)
    expect(html).toContain("Del directorio")
    expect(html).toContain("Del día a día")
  })

  it("y el archivo no escribe ninguna etiqueta de vista por su cuenta", () => {
    const fuente = readFileSync(join(__dirname, "TipoObjetivoTabs.tsx"), "utf-8")
    // Fuera de los comentarios —que sí las nombran para explicar la decisión— no puede haber un
    // literal JSX con el nombre de una vista: eso sería la copia que `/campos` viene a evitar.
    const jsx = fuente.slice(fuente.indexOf("export function"))
    expect(jsx).not.toContain(">Anual<")
    expect(jsx).not.toContain(">Operativo<")
    // Contracara: el corte no dejó el string vacío, o las dos de arriba pasarían solas.
    expect(jsx).toContain(">Todas<")
  })
})

/**
 * ⚠️ EL `value` DE UNA SOLAPA NO SE PUEDE AFIRMAR SOBRE EL MARKUP, y por eso este bloque mira el
 * fuente. `Tabs` de base-ui no emite el value como atributo: lo guarda en su estado y en el DOM
 * deja `aria-controls` con un id generado. Medido al escribir esto — la aserción "el markup
 * contiene 'anual'" fallaba con el componente correcto, que es el peor tipo de test.
 * Que el valor elegido llegue de verdad a la query lo prueba `services/filtros-export.test.ts`,
 * que es donde ese cable se puede ver entero.
 */
describe("Todas es la ausencia del filtro, no un valor", () => {
  const jsx = (() => {
    const f = readFileSync(join(__dirname, "TipoObjetivoTabs.tsx"), "utf-8")
    return f.slice(f.indexOf("export function"))
  })()

  it('la solapa "Todas" vale "" — no "todas", que traería CERO filas del backend', () => {
    expect(jsx).toContain('<Tab value="">Todas</Tab>')
    expect(jsx).not.toContain('value="todas"')
  })

  it("y las otras dos toman su value del catálogo, no de un literal escrito acá", () => {
    expect(jsx).toContain("value={v.value}")
    expect(jsx).not.toContain('value="anual"')
    expect(jsx).not.toContain('value="operativo"')
  })
})

describe("sin catálogo no hay selector", () => {
  it("con la lista vacía no dibuja nada (una barra de una sola solapa no elige nada)", () => {
    expect(render([])).toBe("")
  })

  it("EL CONTRASTE: con catálogo sí dibuja, y con su etiqueta accesible", () => {
    const html = render(VISTAS)
    expect(html).not.toBe("")
    expect(html).toContain('aria-label="Vista de objetivos"')
  })
})
