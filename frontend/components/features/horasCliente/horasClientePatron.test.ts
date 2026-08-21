import { readFileSync } from "node:fs"
import path from "node:path"

import { describe, expect, it } from "vitest"

/**
 * El patrón del bloque B sobre /horas-por-cliente. Lo que esta pantalla YA tenía —los KPIs, el
 * árbol de clientes, el formato del detalle— está cubierto en `horasCliente.test.tsx`; acá va
 * sólo lo que la tanda del patrón cambió.
 *
 * 🔴 (a) (b) Y LOS CHIPS NO APLICAN, Y ES UNA DECISIÓN, NO UNA FALTA. `mes` y `anio` son
 * `Query(...)` **sin default** en `/api/horas-cliente`: sin período la consulta sería la tabla
 * entera y el backend la rechaza. Un chip promete que el filtro se puede QUITAR, y acá quitarlo
 * no deja la pantalla sin filtrar — deja la consulta rota. Mismo caso que el período de /costos.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · que vuelvan los `return` tempranos que se llevaban el encabezado Y el selector de período.
 *   · que el período vuelva a ser dos `<Input type="number">`.
 *   · que el vacío deje de nombrar el mes real y vuelva a "no hay datos".
 *   · que el export deje de compartir el objeto de filtros con el listado.
 */

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "horas-por-cliente", "page.tsx")
const SELECTOR = path.resolve(__dirname, "..", "shared", "PeriodSelector.tsx")

/** El código sin comentarios. Los finales de Windows se normalizan ANTES de nada: con `\r\n` cada
 *  línea termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

const FUENTE = readFileSync(PAGINA, "utf8")
const CODIGO = sinComentarios(FUENTE)

describe("🔴 el encabezado y el selector de período se dibujan SIEMPRE", () => {
  it("no quedan `return` tempranos por carga ni por error", () => {
    /*
     * Eran dos, y el que dolía era el de carga: se llevaba puesto el propio control con el que se
     * elige el mes, o sea que mover el selector hacía desaparecer el selector hasta que volviera
     * la respuesta. El usuario no podía corregir el mes que acababa de elegir mal.
     */
    expect(CODIGO).not.toMatch(/if\s*\(loading\)\s*return/)
    expect(CODIGO).not.toMatch(/if\s*\(error\)\s*return/)
    expect((CODIGO.match(/^\s*return \(/gm) ?? []).length).toBe(1)
  })

  it("el encabezado nombra el período incluso mientras carga", () => {
    // Sin datos todavía, el subtítulo dice el mes elegido: la pantalla contesta "qué estoy
    // mirando" antes de poder contestar "cuánto es".
    expect(CODIGO).toContain("loading || !datos")
    expect(CODIGO).toContain("MESES_LARGOS[mes - 1]")
  })

  it("los tres estados salen de una sola cadena: cargando → error → datos", () => {
    expect(CODIGO).toContain("{loading ? (")
    expect(CODIGO).toContain(") : error || !datos ? (")
    expect(CODIGO).toContain("<Skeleton key={i} shimmer")
  })

  it("🔴 el error trae reintento y NO recarga la app entera", () => {
    expect(CODIGO).toContain("action={load}")
    expect(CODIGO).not.toContain("window.location.reload")
  })
})

describe("🔴 el período es UN control compartido, no dos inputs numéricos", () => {
  it("la página usa `PeriodSelector` y ya no tiene `<Input type=\"number\">`", () => {
    /*
     * Eran dos `<Input type="number">`: había que TIPEAR "3" para ver marzo —el usuario no sabe
     * si el mes va 1..12 o 0..11— y nada impedía escribir 13 o 1901. El selector es el mismo
     * control que /costos, con los meses por nombre y los años acotados.
     */
    expect(CODIGO).toContain("<PeriodSelector")
    expect(CODIGO).not.toContain('type="number"')
  })

  it("y ese control vive en `shared/`, no en el módulo de costos", () => {
    /*
     * Nació en `components/features/costos/`. La segunda pantalla que lo necesitaba no podía
     * importarlo de ahí sin atarse a un módulo que no tiene nada que ver: `costos/PeriodSelector`
     * quedó como re-export para no tocar sus consumidores.
     */
    const compartido = readFileSync(SELECTOR, "utf8")
    expect(compartido).toContain("export function PeriodSelector")
    // Y declara por qué no es un chip, en el archivo mismo y no sólo en este test.
    expect(compartido).toContain("ESTE CONTROL NO ES UN CHIP")

    const enCostos = readFileSync(path.resolve(__dirname, "..", "costos", "PeriodSelector.tsx"), "utf8")
    expect(enCostos).toContain("@/components/features/shared/PeriodSelector")
    // Guarda: si el re-export se hubiera quedado con una copia del componente, esto lo caza.
    expect(enCostos).not.toContain("<select")
  })

  it("⚠️ no monta FiltersBar ni Pagination, y las dos ausencias son correctas", () => {
    // Sin chips por lo de arriba; sin pie porque el endpoint devuelve el agrupamiento entero.
    expect(CODIGO).not.toContain("<FiltersBar")
    expect(CODIGO).not.toContain("<Pagination")
  })
})

describe("(c) el vacío usa el valor real del período, aunque no haya chip de dónde sacarlo", () => {
  it("la frase nombra el mes y el año elegidos", () => {
    expect(FUENTE).toContain("Sin cargas en el período")
    expect(CODIGO).toContain("Nadie cargó horas en ${MESES_LARGOS[mes - 1]} ${anio}")
  })

  it("🔴 el export comparte el MISMO objeto de filtros que el listado", () => {
    // Es la invariante 2 del bloque: si el export armara su período por su cuenta, el archivo
    // podría traer un mes distinto del que se está mirando, sin error y sin aviso.
    expect(CODIGO).toContain("const filtros = { mes, anio }")
    expect(CODIGO).toContain("exportarHorasPorCliente(formato, filtros)")
    expect(CODIGO).toContain("cargarHorasCliente({ mes, anio }")
  })
})
