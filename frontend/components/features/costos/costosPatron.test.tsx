import { readFileSync } from "node:fs"
import path from "node:path"

import { describe, expect, it } from "vitest"

/**
 * El patrón del bloque B sobre /costos, **el caso sin chips de la tanda**.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 (a) Y (b) NO APLICAN, Y ÉSA ES LA DECISIÓN QUE ESTE ARCHIVO FIJA.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * El único filtro de esta pantalla es el PERÍODO, y el backend lo exige: `mes` y `anio` son
 * `Query(...)` **sin default** en los tres endpoints de costos. Un chip promete que el filtro se
 * puede quitar —su ✕ llama al `onChange` con vacío— y acá quitarlo no deja la pantalla sin
 * filtrar: deja la consulta rota. Ponerle chips sería escribir una mentira en la UI.
 *
 * Lo que la pantalla SÍ toma del patrón —y es lo que se verifica acá— es la tabla del detalle de
 * nómina: `patron="datos"`, los anchos declarados, el esqueleto con la misma grilla, el vacío
 * adentro de la tabla y el pie siempre que haya filas.
 *
 * ⚠️ Y NO TIENE TABS: es un dashboard con el detalle abajo, en la misma vista.
 *
 * ⚠️ POR QUÉ ESTE ARCHIVO LEE CÓDIGO Y NO RENDERIZA. `NominaSection` monta `useNominaLista`, que
 * fetchea en un `useEffect`; vitest corre sin jsdom, así que `renderToStaticMarkup` no ejecuta
 * efectos y la tabla saldría siempre en su estado inicial. Lo que sí se puede verificar sin DOM
 * son las DECISIONES, que es lo que este bloque cubre.
 */

const DIR = path.resolve(__dirname)
const PAGINA = path.resolve(DIR, "..", "..", "..", "app", "(dashboard)", "costos", "page.tsx")

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

const seccion = () => readFileSync(path.resolve(DIR, "NominaSection.tsx"), "utf8")

describe("(a) (b) NO APLICAN: el período es obligatorio y no puede ser un chip", () => {
  it("la pantalla no monta <FiltersBar>, y el período sigue en su selector propio", () => {
    const pagina = readFileSync(PAGINA, "utf8")
    expect(sinComentarios(pagina)).not.toContain("<FiltersBar")
    expect(pagina).toContain("<CostosAcciones")
    // Contracara: el archivo leído es el que se cree.
    expect(pagina).toContain("<NominaSection")
  })

  it("y el porqué está escrito donde vive el control, no sólo en un commit", () => {
    // Una decisión de este tipo se pierde si sólo vive en el historial: el próximo que quiera
    // "unificar" el filtro tiene que chocarse con la razón en el archivo.
    const acciones = readFileSync(path.resolve(DIR, "CostosAcciones.tsx"), "utf8")
    expect(acciones).toContain("sin default")
    expect(acciones).toContain("deja la consulta rota")
  })
})

describe("(c) el detalle de nómina usa el patrón de tabla", () => {
  it("una sola <Table patron='datos'> para los tres estados, con la grilla compartida", () => {
    const src = sinComentarios(seccion())
    expect(src).toContain('<Table patron="datos">')
    expect(src).toContain("<Encabezado columnas={columnas} />")
    expect(src).toContain("<FilasEsqueleto columnas={columnas} />")
    // Las columnas salen de UNA lista: encabezado, esqueleto y filas reales leen la misma.
    expect(src).toContain("COLUMNAS_NOMINA")
  })

  it("🔴 el vacío es una fila con colSpan y NOMBRA el período: es el valor real del filtro", () => {
    /*
     * No usa `TablaVacia` porque no hay chips de dónde sacar la frase, pero conserva las dos
     * cosas que el patrón busca: el texto con el VALOR REAL ("No hay nómina cargada para Marzo
     * 2026") y la estructura —fila con `colSpan`, `data-vacio`, encabezado intacto—.
     */
    const src = seccion()
    expect(src).toContain('<TableRow data-vacio=""')
    expect(src).toContain("colSpan={columnas.length}")
    expect(src).toContain("No hay nómina cargada para ${MESES_LARGOS[mes - 1]} ${anio}")
  })

  it("la columna de acciones desaparece sin permiso de escritura", () => {
    // Una columna vacía con su encabezado es una promesa que la pantalla no cumple.
    expect(sinComentarios(seccion())).toContain('c.clave !== "acciones" || canWrite')
  })
})

describe("(d) el contador del pie sale de `total`, nunca de filas.length", () => {
  it("le pasa `total={n.total}` a <Pagination>", () => {
    const jsx = seccion().match(/<Pagination[\s\S]*?\/>/)
    expect(jsx, "el detalle de nómina dejó de renderizar <Pagination>").not.toBeNull()
    expect(jsx![0]).toContain("total={n.total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0])).toBe(false)
  })

  it("🔴 el pie va SIEMPRE que haya filas, y NUNCA sobre el esqueleto", () => {
    /*
     * Era `n.total > PAGE_SIZE`. La guarda de carga importa especialmente acá: al cambiar de mes
     * la lista se vuelve a pedir, y sin ella la barra queda mostrando el total del período
     * ANTERIOR encima del esqueleto del nuevo.
     */
    const src = sinComentarios(seccion())
    expect(src).toContain("!n.loading && n.filas.length > 0 && (")
    expect(src).not.toContain("n.total > PAGE_SIZE")
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría la negación de arriba.
    expect(sinComentarios("if (n.total > PAGE_SIZE) {}")).toContain("n.total > PAGE_SIZE")
  })

  it("y el contador del encabezado también sale de `total`, no del largo de la página", () => {
    // En la página 2 el largo del array es 20 y el encabezado diría "20 registros" siempre.
    expect(sinComentarios(seccion())).toContain("{n.total} registro")
  })
})
