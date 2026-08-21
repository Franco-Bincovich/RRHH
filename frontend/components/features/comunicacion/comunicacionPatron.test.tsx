import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { PlantillaCard } from "./PlantillaCard"

/**
 * El patrón del bloque B sobre /comunicacion, que tiene DOS pestañas con formas distintas:
 * **Plantillas es TARJETAS** (§5) y **Historial es tabla**.
 *
 * ⚠️ (a) (b) y (d) NO APLICAN A PLANTILLAS: `GET /api/plantillas` no acepta un solo Query y
 * devuelve la lista entera, así que no hay chips ni pie. Los chips del Historial —que sí filtra
 * server-side— están cubiertos por `HistorialTabla.test.tsx`, que se actualizó en esta tanda para
 * recibirlos.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · que las plantillas volvieran a ser filas dentro del acordeón: reaparece `ConfigSection`.
 *   · que el badge "General" volviera a ser un relleno.
 *   · que las acciones volvieran a aparecer sólo en hover.
 */

const SECTION = path.resolve(__dirname, "PlantillasSection.tsx")
const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "comunicacion", "page.tsx")

const PLANTILLA = {
  id: "p1", clave: "bienvenida", asunto: "Bienvenida a {{empresa_nombre}}",
  cuerpo: "", es_global: true, contexto: "empleado",
} as Parameters<typeof PlantillaCard>[0]["plantilla"]

function card(editable: boolean) {
  return renderToStaticMarkup(
    <PlantillaCard plantilla={PLANTILLA} editable={editable} onEditar={() => {}} onEnviar={() => {}} />,
  )
}

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("🔴 Plantillas es TARJETAS, no filas dentro de un acordeón", () => {
  it("la sección monta GrillaTarjetas y ya no usa ConfigSection", () => {
    /*
     * §5 nombra a comunicación junto a perfiles de puesto y reportes: "cada plantilla de mail
     * guardada, una tarjeta". Hasta el 21/8/2026 era una lista de filas envuelta en
     * `ConfigSection` —la shell plegable de /configuracion—, y el propio archivo ya anotaba que
     * el acordeón sobraba y que sacarlo quedaba pendiente para no mezclarlo con la mudanza.
     */
    const src = sinComentarios(readFileSync(SECTION, "utf8"))
    expect(src).toContain("<GrillaTarjetas>")
    expect(src).toContain("<PlantillaCard")
    expect(src).not.toContain("ConfigSection")
  })

  it("y el `Accordion.Root` que la envolvía se fue de la página", () => {
    const src = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(src).not.toContain("Accordion")
    // Contracara: el archivo leído es el que se cree.
    expect(src).toContain("<PlantillasSection")
  })

  it("el esqueleto son tarjetas del mismo alto, con shimmer y no con el pulse de 2s", () => {
    const src = sinComentarios(readFileSync(SECTION, "utf8"))
    expect(src).toContain("<Skeleton key={i} shimmer")
    expect(src).toContain("h-28")
  })
})

describe("(c) el vacío dice lo que la ausencia SIGNIFICA", () => {
  it("copy propio: sin plantillas el sistema no le puede escribir a nadie", () => {
    /*
     * Esta pantalla no tiene filtros, así que `textoVacio` sólo podría dar su rama genérica
     * —"Cuando se cargue la primera va a aparecer acá"— y ahí se pierde lo único que importa:
     * sin plantillas los envíos de esta pantalla no existen. Para `gerencia_lectura`, que no
     * puede crearlas, la frase sigue siendo cierta y no le pide nada.
     */
    const src = readFileSync(SECTION, "utf8")
    expect(src).toContain("Todavía no hay plantillas cargadas")
    expect(src).toContain("el sistema no tiene con qué escribirle a la gente")
    expect(sinComentarios(src)).not.toContain("Cuando se cargue la primera")
  })
})

describe("la tarjeta: acciones siempre visibles y ningún relleno azul", () => {
  it("con permiso muestra enviar y editar, y las dos cambian de color al apuntar", () => {
    const html = card(true)
    expect(html).toContain("Enviar bienvenida")
    expect(html).toContain("Editar bienvenida")
    // Siempre visibles: lo que hace el hover es subir el contraste, no revelarlas.
    expect(html).toContain("group-hover:text-primary")
  })

  it("sin permiso no ofrece ninguna de las dos — el backend las gatea con el mismo permiso", () => {
    // Un botón de enviar visible para `gerencia_lectura` daría 403 al apretarlo.
    const html = card(false)
    expect(html).not.toContain("Enviar bienvenida")
    expect(html).not.toContain("Editar bienvenida")
    // Guarda: sin esto, un componente que devuelve "" pasaría las dos negaciones.
    expect(html).toContain("bienvenida")
  })

  it("🔴 el badge 'General' es contorno, no relleno azul", () => {
    const html = card(false)
    expect(html).toContain("General")
    expect(html).not.toContain("bg-primary")
  })

  it("el asunto se lee entero, no truncado en una celda", () => {
    // Es el texto que la persona ve en su bandeja: es lo que se viene a revisar antes de mandar.
    expect(card(false)).toContain("line-clamp-2")
  })
})

describe("(a) (b) (d) NO APLICAN a Plantillas: no filtra ni pagina", () => {
  it("la sección no monta <FiltersBar> ni <Pagination>, y eso es lo correcto", () => {
    // `GET /api/plantillas` no acepta un solo Query. Ponerle chips sería inventar filtros que el
    // backend no puede honrar, y un pie tendría que derivarse del array ya traído.
    const src = readFileSync(SECTION, "utf8")
    expect(src).not.toContain("<FiltersBar")
    expect(src).not.toContain("<Pagination")
  })

  it("el Historial SÍ tiene panel de chips: sus dos filtros son server-side", () => {
    const src = sinComentarios(readFileSync(path.resolve(__dirname, "HistorialMails.tsx"), "utf8"))
    expect(src).toContain("<FiltersBar campos={campos} panel")
    expect(src).toContain("chipsDeCampos(campos)")
    // Y el vacío del historial pasa a nombrar el filtro: está cubierto en HistorialTabla.test.
    expect(src).toContain("onLimpiarTodo")
  })
})
