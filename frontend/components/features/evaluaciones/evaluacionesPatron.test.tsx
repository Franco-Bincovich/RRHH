import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import { construirCamposEvaluados, type ArgsCamposEvaluados } from "./resultados/_camposEvaluados"
import { EvaluadosResultadosTable } from "./resultados/EvaluadosResultadosTable"

/**
 * Los cuatro puntos del patrón del bloque B sobre /evaluaciones, MÁS la regla de vocabulario
 * propia de este módulo: **el sistema no corre evaluaciones, importa resultados**.
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCamposEvaluados`, EL CABLEADO REAL. Con campos inventados el
 * chip llamaría a un `onChange` de mentira y el test pasaría con el cableado roto.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (c) que el vacío volviera a reemplazar la tabla entera: desaparece `<thead>`.
 *   · (d) que el panel le pasara `items.length` a `<Pagination>`.
 *   · vocabulario: que alguien reponga la palabra "ciclo" en cualquier texto visible.
 */

const PROYECTOS = [{ id: "pr1", nombre: "Karstec" }]
const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "evaluaciones", "page.tsx")
const PANEL = path.resolve(__dirname, "resultados", "EvaluadosResultadosPanel.tsx")

function args(over: Partial<ArgsCamposEvaluados> = {}): ArgsCamposEvaluados {
  return {
    sectores: ["Ventas", "Sistemas"],
    sector: "", setSector: vi.fn(),
    perfil: "", setPerfil: vi.fn(),
    conNota: "", setConNota: vi.fn(),
    proyectos: PROYECTOS as ArgsCamposEvaluados["proyectos"], proyecto: "", setProyecto: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

describe("(a) los chips muestran el label legible, no el value crudo", () => {
  it("Perfil dice 'Líder' y Nota final dice 'Sin nota', no 'lider' ni 'no'", () => {
    const chips = chipsDeCampos(construirCampos_(args({ perfil: "lider", conNota: "no" })))
    expect(chips.find((c) => c.clave === "Perfil")!.valor).toBe("Líder")
    expect(chips.find((c) => c.clave === "Nota final")!.valor).toBe("Sin nota")
  })

  it("el Proyecto dice el nombre y no el uuid", () => {
    const chips = chipsDeCampos(construirCampos_(args({ proyecto: "pr1" })))
    expect(chips.find((c) => c.clave === "Proyecto")!.valor).toBe("Karstec")
  })
})

// Alias local: el nombre largo del import haría ilegible cada llamada de abajo.
const construirCampos_ = construirCamposEvaluados

describe("(b) quitar un chip quita ESE filtro, no los otros, y resetea a página 1", () => {
  it("quitar Perfil no toca Sector", () => {
    const a = args({ perfil: "lider", sector: "Ventas" })
    chipsDeCampos(construirCampos_(a)).find((c) => c.clave === "Perfil")!.quitar()
    expect(a.setPerfil).toHaveBeenCalledWith("")
    expect(a.onFiltroChange).toHaveBeenCalled()
    expect(a.setSector).not.toHaveBeenCalled()
  })

  it("vale para TODOS los filtros con chip", () => {
    const a = args({ sector: "Ventas", perfil: "general", conNota: "si", proyecto: "pr1" })
    const chips = chipsDeCampos(construirCampos_(a))
    // Guarda contra el falso verde: sin chips, el for de abajo no compara nada.
    expect(chips.length).toBe(4)
    for (const chip of chips) {
      const antes = (a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length
      chip.quitar()
      expect((a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length, `el chip "${chip.etiqueta}" no reseteó la página`).toBe(antes + 1)
    }
  })

  it("qué queda atrás de 'Más filtros': sólo Proyecto, que cruza con otro módulo", () => {
    const campos = construirCampos_(args())
    expect(campos.filter((c) => c.avanzado).map((c) => c.label)).toEqual(["Proyecto"])
    expect(campos.filter((c) => !c.avanzado).map((c) => c.label)).toEqual(["Sector", "Perfil", "Nota final"])
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

function tabla(props: Partial<Parameters<typeof EvaluadosResultadosTable>[0]> = {}) {
  return renderToStaticMarkup(
    <EvaluadosResultadosTable
      items={[]} loading={false} onFicha={() => {}}
      chips={[chip("Sector", "Ventas")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos mantiene el encabezado y usa los valores reales", () => {
  it("las columnas siguen ahí y el vacío es una fila de la tabla", () => {
    const html = tabla()
    for (const columna of ["Evaluado", "Sector", "Superior", "Evaluadores", "Nota final"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
    expect(html).toContain('colSpan="6"')
  })

  it("la frase arranca impersonal: el recorte por empresa lo hace el LOTE, no un chip", () => {
    expect(tabla()).toContain("No hay evaluados con sector Ventas.")
  })

  it("el esqueleto tiene la misma cantidad de columnas que la tabla", () => {
    const cargando = tabla({ loading: true })
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(6)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 6)
    expect(cargando).toContain("animate-shimmer")
  })
})

describe("🔴 la pantalla NO insinúa que el sistema corra evaluaciones", () => {
  it("no queda la palabra 'ciclo' en ningún texto visible", () => {
    /*
     * §7 del sistema de diseño es explícito: el sistema **IMPORTA resultados calculados afuera**,
     * no los corre. "Ciclo" nombra un proceso que la herramienta abriría, seguiría y cerraría
     * —con instancias, vencimientos y recordatorios— y **nada de eso existe**: no hay evaluaciones
     * pendientes ni vencidas que mostrar. Decía "Ciclo" en el selector, "métricas del ciclo" en el
     * subtítulo y "los archivos de un ciclo" en el vacío.
     *
     * 🔑 Se mira el texto VISIBLE, no el archivo entero: los comentarios explican por qué la
     * palabra no va, así que la contienen. Marcarlos empujaría a borrar la explicación.
     */
    const visible = readFileSync(PAGINA, "utf8")
      .replace(/\r\n/g, "\n")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
    expect(visible.toLowerCase()).not.toContain("ciclo")
    // Y dice lo que la pantalla ES.
    expect(visible).toContain("Período importado")
    expect(visible).toContain("el sistema no corre las evaluaciones")
    // Contracara: la prosa SÍ menciona la palabra, y eso es correcto.
    expect(readFileSync(PAGINA, "utf8").toLowerCase()).toContain("ciclo")
  })
})

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(d) el contador del pie sale de `total`, nunca de items.length", () => {
  it("el panel le pasa `total={total}` a <Pagination>", () => {
    const jsx = readFileSync(PANEL, "utf8").match(/<Pagination[\s\S]*?\/>/)
    expect(jsx, "el panel dejó de renderizar <Pagination>").not.toBeNull()
    expect(jsx![0]).toContain("total={total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0])).toBe(false)
  })

  it("🔴 el pie va SIEMPRE que haya filas, y NUNCA sobre el esqueleto", () => {
    const codigo = sinComentarios(readFileSync(PANEL, "utf8"))
    expect(codigo).toContain("!cargando && items.length > 0 && (")
    expect(codigo).not.toContain("total > PAGE_SIZE")
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría la negación de arriba.
    expect(sinComentarios("if (total > PAGE_SIZE) {}")).toContain("total > PAGE_SIZE")
  })
})
