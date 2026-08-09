/**
 * La regla del módulo, hecha test: es un FILTRO DE DESCARTE, no una decisión.
 *
 * 🚨 ¿Qué tendría que ser distinto para que estos tests puedan fallar? Se afirma sobre el
 * MARKUP renderizado, no sobre las constantes del componente: si alguien atenúa `no_relevante`,
 * lo pinta de rojo, o saca la leyenda de la pantalla, el markup cambia y esto se rompe. Un test
 * que comparara `ESTILOS.no_relevante` contra una constante copiada acá no probaría nada.
 *
 * ⚠️ `vitest` corre con `environment: "node"` y sin jsdom: esto verifica el markup, no la
 * interacción, y NO ejecuta `useEffect`. Los dos componentes de acá son puros, así que alcanza.
 */
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { ClasificacionBadge, LeyendaDescarte } from "./ClasificacionBadge"

describe("ClasificacionBadge", () => {
  it("muestra las tres categorías con su etiqueta legible", () => {
    expect(renderToStaticMarkup(<ClasificacionBadge clasificacion="relevante" />)).toContain("Relevante")
    expect(renderToStaticMarkup(<ClasificacionBadge clasificacion="dudoso" />)).toContain("Dudoso")
    expect(renderToStaticMarkup(<ClasificacionBadge clasificacion="no_relevante" />)).toContain("No relevante")
  })

  it("🔴 no_relevante NO se pinta de rojo ni se atenúa: no es un veredicto", () => {
    const html = renderToStaticMarkup(<ClasificacionBadge clasificacion="no_relevante" />)
    // Se afirma sobre los tokens de PINTADO, no sobre la subcadena "destructive" a secas: el
    // primitivo de shadcn ya trae `aria-invalid:border-destructive` en su clase base, que es
    // boilerplate del componente y no una decisión de este módulo. Lo que no puede aparecer es
    // un fondo/texto rojo o un atenuado — cualquiera de los dos lo haría leer como "descartado".
    for (const token of ["bg-destructive", "text-destructive", "bg-red", "text-red", "opacity-"]) {
      expect(html).not.toContain(token)
    }
  })

  it("🔴 las tres usan el MISMO variant del primitivo: ninguna pesa más que otra", () => {
    const variantes = (["relevante", "dudoso", "no_relevante"] as const).map(
      (c) => renderToStaticMarkup(<ClasificacionBadge clasificacion={c} />).match(/data-variant="(\w+)"/)?.[1],
    )
    expect(new Set(variantes).size).toBe(1)
  })

  it("🔴 los TRES estados sin clasificación dicen cosas distintas", () => {
    // Cada uno pide una acción distinta: apretar el botón · pedir otro CV · reintentar. Antes
    // los tres decían "Sin clasificar" y el tercero además se perdía al recargar la página.
    const textos = [
      renderToStaticMarkup(<ClasificacionBadge clasificacion={null} />),
      renderToStaticMarkup(<ClasificacionBadge clasificacion={null} sinTexto />),
      renderToStaticMarkup(<ClasificacionBadge clasificacion={null} fallo />),
    ]
    expect(textos[0]).toContain("Sin clasificar")
    expect(textos[1]).toContain("CV no legible")
    expect(textos[2]).toContain("No se pudo clasificar")
    expect(new Set(textos).size).toBe(3)
  })

  it("un CV ilegible manda sobre el fallo: es la causa raíz y dice qué hacer", () => {
    const html = renderToStaticMarkup(<ClasificacionBadge clasificacion={null} sinTexto fallo />)
    expect(html).toContain("CV no legible")
  })
})

describe("LeyendaDescarte", () => {
  const html = renderToStaticMarkup(<LeyendaDescarte />)

  it("🔴 dice que no es una decisión, con esas palabras", () => {
    expect(html).toContain("filtro de descarte, no una decisión")
  })

  it("🔴 pide explícitamente revisar también los no relevantes", () => {
    expect(html).toContain("incluidos los marcados como no relevantes")
  })

  it("🔴 es texto visible, no un tooltip", () => {
    // Si alguien la mueve a un `title=` o a un tooltip, el texto deja de estar en el cuerpo del
    // markup y esto falla. Que se lea sin pasar el mouse es el punto entero de la leyenda.
    expect(html).not.toContain("title=")
    expect(html).toContain("<p")
  })
})
