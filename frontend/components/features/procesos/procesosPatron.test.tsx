import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { ESTADO_COLOR, ProcesoCard } from "./ProcesoCard"

/**
 * El patrón del bloque B sobre /procesos, que es **TARJETAS, no una tabla** (§5): cada tarjeta es
 * un módulo del sistema con el desglose de sus estados.
 *
 * ⚠️ (a) (b) y (d) NO APLICAN, y no es un olvido: `GET /api/procesos/resumen` no acepta un solo
 * Query — devuelve los cuatro conteos y nada más. No hay nada que filtrar ni que paginar.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · que los puntitos de estado vuelvan a la escala cruda (`bg-blue-500`, `bg-green-500`).
 *   · (c) que el vacío vuelva a decir "todavía no hay procesos", que acá es falso: nadie CARGA
 *     un proceso — este panel cuenta lo que está abierto en los otros módulos.
 *   · que el error vuelva a dibujarse sin reintento.
 */

const PROCESO = {
  clave: "onboarding", label: "Onboarding", total: 7,
  estados: [
    { estado: "en_curso", label: "En curso", total: 5 },
    { estado: "completado", label: "Completado", total: 2 },
  ],
} as unknown as Parameters<typeof ProcesoCard>[0]["proceso"]

describe("la tarjeta de un proceso", () => {
  it("dice el total arriba y el desglose por estado abajo", () => {
    const html = renderToStaticMarkup(<ProcesoCard proceso={PROCESO} />)
    expect(html).toContain("Onboarding")
    expect(html).toContain("7")
    expect(html).toContain("En curso")
    expect(html).toContain("Completado")
  })

  it("los números van con cifras tabulares: la columna se compara de un vistazo", () => {
    expect(renderToStaticMarkup(<ProcesoCard proceso={PROCESO} />)).toContain("tabular-nums")
  })
})

describe("🔴 los colores de estado salen de la paleta semántica", () => {
  const CRUDOS = ["blue", "green", "red", "amber", "emerald", "slate", "rose"]

  it("ninguno es un color de la escala cruda de Tailwind", () => {
    const clases = Object.values(ESTADO_COLOR)
    // Guarda contra el falso verde: si el mapa quedara vacío, el for no compara nada.
    expect(clases.length).toBeGreaterThanOrEqual(4)
    for (const clase of clases) {
      for (const crudo of CRUDOS) {
        expect(clase, `"${clase}" volvió a la escala cruda de Tailwind`).not.toContain(crudo)
      }
    }
  })

  it("y los estados siguen distinguiéndose entre sí", () => {
    // Contracara: mapear todo a `bg-muted` pasaría la negación de arriba y borraría el desglose.
    expect(new Set(Object.values(ESTADO_COLOR)).size).toBeGreaterThanOrEqual(3)
  })
})

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "procesos", "page.tsx")

describe("(c) el vacío tiene copy propio: acá nadie CARGA un proceso", () => {
  it("la frase nombra de dónde salen los procesos en vez de pedir que se cargue el primero", () => {
    const src = readFileSync(PAGINA, "utf8")
    expect(src).toContain("No hay ningún proceso abierto")
    expect(src).toContain("Este panel cuenta lo que está en curso en los otros módulos")
    expect(sinComentarios(src)).not.toContain("Cuando se cargue el primero")
  })

  it("🔴 el error trae reintento, y el reintento vuelve a disparar la carga", () => {
    /*
     * La función de carga salió del `useEffect` para que el botón pueda llamarla. Antes el error
     * de esta pantalla no tenía salida: había que recargar el navegador entero.
     */
    const src = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(src).toContain("<ErrorState description={error} action={cargar} />")
    expect(src).toContain("const cargar = useCallback(")
    expect(src).not.toContain("window.location.reload")
  })

  it("es una grilla de tarjetas y su esqueleto tiene esa misma forma", () => {
    const src = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(src).toContain("<GrillaTarjetas>")
    expect(src).toContain("<Skeleton key={i} shimmer")
    // §5: tarjetas, no tabla.
    expect(src).not.toContain("<Table")
  })

  it("⚠️ y no monta filtros ni pie, que es lo correcto para este panel", () => {
    const src = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(src).not.toContain("<FiltersBar")
    expect(src).not.toContain("<Pagination")
  })
})
