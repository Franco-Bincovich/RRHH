import { readFileSync } from "node:fs"
import path from "node:path"

import { describe, expect, it } from "vitest"

/**
 * El patrón del bloque B sobre /organigrama, que es **TARJETAS Y ÁRBOL, no una tabla** (§5).
 *
 * ⚠️ (a) (b) y (d) NO APLICAN, y no es un olvido: el organigrama se arma con el árbol entero —no
 * hay Query que aceptar ni páginas que recorrer—. El selector de proyecto que tiene arriba no es
 * un filtro del listado: **elige qué árbol se dibuja**, que es otra cosa; sin uno elegido no hay
 * nada que mostrar, igual que el período obligatorio de /costos. Por eso no lleva chip.
 *
 * 🔴 LOS 26 HEX DE `colorEmpresa` NO SE TOCAN, y hay un test abajo que lo fija. No son estado en
 * una escala mal→bien —eso sí se migró a la paleta semántica en /procesos y /sucesion—: son
 * IDENTIDAD, un color por empresa, sin orden ni significado. La paleta semántica tiene tres
 * colores; las empresas son hasta 26.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · que vuelvan los `return` tempranos que se llevaban puesto el encabezado.
 *   · que el vacío vuelva a la frase genérica y deje de decir de dónde sale el árbol.
 *   · que alguien "unifique" los hex de `colorEmpresa` con los tokens del sistema.
 */

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "organigrama", "page.tsx")

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

const FUENTE = readFileSync(PAGINA, "utf8")
const CODIGO = sinComentarios(FUENTE)

describe("los tres estados de la vista por proyecto", () => {
  it("el esqueleto tiene la forma del árbol —una raíz y tres hijos— y usa shimmer", () => {
    expect(CODIGO).toContain("function OrgSkeleton()")
    expect(CODIGO).toContain("<Skeleton shimmer")
    expect(CODIGO).not.toContain("animate-pulse")
  })

  it("🔴 el error trae reintento, y el reintento vuelve a pedir los proyectos", () => {
    /*
     * La carga aceptó un `forzar` justamente para esto: sin él, volver a llamarla no hacía nada
     * porque ya había una lista (vacía) en memoria, así que el botón de reintentar habría sido
     * un botón que no arregla nada — peor que no ofrecerlo.
     */
    expect(CODIGO).toContain("<ErrorState")
    expect(CODIGO).toContain("cargarProyectos(true)")
  })

  it("(c) el vacío dice de dónde sale el árbol en vez de pedir que se cargue el primero", () => {
    expect(FUENTE).toContain("Todavía no hay nada que dibujar")
    expect(FUENTE).toContain("se arma con las asignaciones")
    expect(CODIGO).not.toContain("Cuando se cargue el primero")
  })

  it("el encabezado se dibuja SIEMPRE: no hay `return` temprano por carga ni por error", () => {
    expect(CODIGO).not.toMatch(/if\s*\(loading\)\s*return/)
    expect(CODIGO).not.toMatch(/if\s*\(error\)\s*return/)
    expect(CODIGO).toContain("<PageHeader")
  })
})

describe("🔴 los 26 hex de `colorEmpresa` siguen intactos", () => {
  const PALETA = path.resolve(__dirname, "..", "..", "..", "utils", "colorEmpresa.ts")

  it("la paleta de identidad sigue siendo hex y NO tokens del sistema", () => {
    /*
     * Un color por empresa, aplicado con `style` inline. Migrarlos a `--success`/`--warning`/
     * `--danger` no es una mejora: son tres tokens para hasta 26 empresas, y además esos tres
     * SIGNIFICAN algo (bien/atención/mal) que acá no aplica — la empresa 3 no está peor que la 1.
     */
    const src = readFileSync(PALETA, "utf8")
    const hex = src.match(/#[0-9a-fA-F]{6}/g) ?? []
    expect(hex.length, "se perdieron colores de la paleta de identidad").toBe(26)
    /*
     * 26 literales = 8 empresas × 3 (fondo, texto, punto) + los 2 del tag "N proy.".
     * ⚠️ NO se afirma que los 26 sean DISTINTOS, y eso es a propósito: `#854F0B` aparece dos
     * veces —el texto ámbar de la cuarta empresa y el del tag—, y esa repetición es deliberada.
     * Lo que sí tiene que ser único es el color de PUNTO de cada empresa, que es por donde el
     * ojo las distingue en el árbol; eso se mide abajo.
     */
    const dots = src.match(/dot: "(#[0-9a-fA-F]{6})"/g) ?? []
    expect(dots.length).toBe(8)
    expect(new Set(dots.map((d) => d.toLowerCase())).size).toBe(dots.length)
  })
})

describe("⚠️ el selector de proyecto NO es un chip, y no puede serlo", () => {
  it("la página no monta FiltersBar ni Pagination", () => {
    /*
     * Mismo caso que el período obligatorio de /costos y /horas-por-cliente: sin proyecto elegido
     * no hay consulta que hacer, así que no es un filtro que se pueda "quitar" — quitarlo dejaría
     * la pantalla sin nada que dibujar y el chip prometería una vista consolidada que no existe.
     */
    expect(CODIGO).not.toContain("<FiltersBar")
    expect(CODIGO).not.toContain("<Pagination")
  })
})
