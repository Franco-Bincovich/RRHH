import { readFileSync } from "node:fs"
import path from "node:path"

import { describe, expect, it } from "vitest"

/**
 * El patrón del bloque B sobre /offboarding.
 *
 * ⚠️ (a) (b) y (d) NO APLICAN, y no es un olvido: `GET /api/offboarding/instancias` no acepta un
 * solo Query — devuelve la lista entera. Sin filtros no hay chips y sin paginado no hay pie.
 *
 * 🔴 ES UN TEST QUE LEE LA FUENTE, y no uno que renderiza. La pantalla es una `page.tsx` con su
 * fetch adentro: vitest corre SIN jsdom, así que el `useEffect` no se ejecuta y un render a
 * string sale con el esqueleto congelado. Lo que sí se puede afirmar sobre el archivo real es lo
 * que esta tanda cambió: que los tres estados existen, que el vacío dice lo que la ausencia
 * significa, y que el encabezado ya no desaparece mientras carga.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · que vuelvan los `return` tempranos que se llevaban puesto el encabezado.
 *   · que el vacío vuelva a la frase genérica de `textoVacio`.
 *   · que el error vuelva a quedarse sin reintento.
 */

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "offboarding", "page.tsx")

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

const FUENTE = readFileSync(PAGINA, "utf8")
const CODIGO = sinComentarios(FUENTE)

describe("🔴 el encabezado se dibuja SIEMPRE, también mientras carga y con error", () => {
  it("no quedan `return` tempranos antes del <PageHeader>", () => {
    /*
     * Tenía dos: `if (loading) return <...>` y `if (error) return <...>`. Con ellos la pantalla
     * cambiaba de forma tres veces —cargando, error, datos— y el usuario perdía el título y el
     * contexto justo cuando más lo necesita. Ahora el encabezado es fijo y lo único que cambia es
     * el bloque de abajo.
     */
    // El único `return (` del componente es el que abre el JSX, y el encabezado es lo primero
    // que hay adentro. Los dos que se sacaron eran `if (loading) return` / `if (error) return`.
    expect(CODIGO).not.toMatch(/if\s*\(loading\)\s*return/)
    expect(CODIGO).not.toMatch(/if\s*\(error\)\s*return/)
    expect((CODIGO.match(/^\s*return \(/gm) ?? []).length).toBe(1)
    expect(CODIGO).toContain("<PageHeader")
  })

  it("los tres estados están y son excluyentes", () => {
    // Una sola cadena ternaria: cargando → error → vacío → datos. Nunca dos a la vez.
    expect(CODIGO).toContain("{loading ? (")
    expect(CODIGO).toContain(") : error ? (")
    expect(CODIGO).toContain(") : offboardings.length === 0 ? (")
  })
})

describe("(c) el vacío dice lo que la ausencia SIGNIFICA", () => {
  it("copy propio: acá el vacío es una buena noticia, no una lista sin cargar", () => {
    /*
     * `textoVacio` diría "Todavía no hay procesos · Cuando se cargue el primero va a aparecer
     * acá", y eso manda al usuario a buscar un botón de alta que no existe en esta pantalla: un
     * offboarding se inicia desde la ficha del colaborador. Y sobre todo: cero salidas en curso
     * no es un dato faltante.
     */
    expect(FUENTE).toContain("No hay ninguna salida en curso")
    expect(FUENTE).toContain("desde la ficha de un colaborador")
    expect(CODIGO).not.toContain("Cuando se cargue el primero")
  })

  it("el esqueleto usa el shimmer del patrón y no el pulse de 2s", () => {
    expect(CODIGO).toContain("<Skeleton shimmer")
    expect(CODIGO).not.toContain("animate-pulse")
  })

  it("🔴 el error trae su reintento, y el reintento NO recarga la app entera", () => {
    /*
     * Era `action={() => window.location.reload()}`: para arreglar UN fetch fallido recargaba
     * todo, perdiendo el modo del sidebar, el scroll y cualquier modal abierto. La carga salió
     * del efecto de `useOffboardings` y ahora el botón llama a `recargar`.
     */
    expect(CODIGO).toContain("<ErrorState description={error} action={recargar} />")
    expect(CODIGO).not.toContain("window.location.reload")
  })
})

describe("⚠️ (a) (b) y (d) no aplican: esta pantalla no filtra ni pagina", () => {
  it("no monta FiltersBar ni Pagination, y eso es lo correcto", () => {
    expect(CODIGO).not.toContain("<FiltersBar")
    expect(CODIGO).not.toContain("<Pagination")
  })

  it("el contador del encabezado sale del largo de la lista, que acá SÍ es el total", () => {
    // Es el único caso en que `.length` es el total: el endpoint no pagina, devuelve todo.
    expect(CODIGO).toContain("offboardings.length")
  })
})
