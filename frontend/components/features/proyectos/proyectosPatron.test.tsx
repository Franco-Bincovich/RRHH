import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import { construirCampos, type ArgsCamposProyectos } from "./_camposProyectos"
import { ProyectosGrid } from "./ProyectosGrid"

/**
 * Los cuatro puntos del patrón del bloque B sobre /proyectos, con la vuelta propia de esta
 * pantalla: **no es una tabla, son tarjetas** (§5), así que (c) no puede verificar un `<thead>`
 * que no existe. Lo que sí se verifica es lo que el patrón deja igual: el TEXTO del vacío sale de
 * `textoVacio()` con los mismos chips, y las dos salidas se ofrecen sin ejecutarse.
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos`, EL CABLEADO REAL. Con campos inventados el chip
 * llamaría a un `onChange` de mentira y el test pasaría con el cableado roto.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (a) que el chip mostrara `campo.value` (el uuid del área) en vez de su nombre.
 *   · (b) que un `onChange` se olvidara de `onFiltroChange`.
 *   · (c) que el vacío volviera al literal "No hay proyectos registrados": es verdadero con tres
 *     filtros puestos y no dice cuál de los tres dejó la pantalla en cero.
 *   · (d) que la página le pasara `proyectos.length` a `<Pagination>`, o que sacara la guarda de
 *     `!loading` y volviera a dibujar el pie sobre el esqueleto con el total del pedido anterior.
 */

const EMPRESAS = [{ id: "e1", nombre: "Karstec" }, { id: "e2", nombre: "Dosuba" }]
const AREAS = [{ id: "a1", nombre: "Sistemas", empresa_id: "e1" }]

function args(over: Partial<ArgsCamposProyectos> = {}): ArgsCamposProyectos {
  return {
    empresaActivaId: null, empresas: EMPRESAS as ArgsCamposProyectos["empresas"],
    empresaFiltro: "", setEmpresaFiltro: vi.fn(),
    estadoFiltro: "", setEstadoFiltro: vi.fn(),
    areas: AREAS as ArgsCamposProyectos["areas"], areaFiltro: "", setAreaFiltro: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

describe("(a) los chips muestran el label legible, no el value crudo", () => {
  it("Empresa y Área dicen el nombre; Estado dice 'Pausado' y no 'pausado'", () => {
    const chips = chipsDeCampos(construirCampos(args({ empresaFiltro: "e1", areaFiltro: "a1", estadoFiltro: "pausado" })))
    expect(chips.find((c) => c.clave === "Empresa")!.valor).toBe("Karstec")
    expect(chips.find((c) => c.clave === "Área")!.valor).toBe("Sistemas")
    expect(chips.find((c) => c.clave === "Estado")!.valor).toBe("Pausado")
  })

  it("sin nada elegido no hay ningún chip: la fila inferior del panel no aparece", () => {
    // Contracara: sin esto, un `chipsDeCampos` que devolviera siempre tres chips pasaría todo lo
    // de arriba y el contador de filtros activos se mostraría con la pantalla sin filtrar.
    expect(chipsDeCampos(construirCampos(args()))).toEqual([])
  })
})

describe("(b) quitar un chip quita ESE filtro, no los otros, y resetea a página 1", () => {
  it("el chip de Estado llama a su setter con vacío y dispara el reset", () => {
    const a = args({ estadoFiltro: "activo", areaFiltro: "a1" })
    chipsDeCampos(construirCampos(a)).find((c) => c.clave === "Estado")!.quitar()

    expect(a.setEstadoFiltro).toHaveBeenCalledWith("")
    expect(a.onFiltroChange).toHaveBeenCalled()
    expect(a.setAreaFiltro).not.toHaveBeenCalled()
  })

  it("vale para TODOS los filtros con chip, no sólo para Estado", () => {
    const a = args({ empresaFiltro: "e1", estadoFiltro: "activo", areaFiltro: "a1" })
    const chips = chipsDeCampos(construirCampos(a))
    // Guarda contra el falso verde: sin chips, el for de abajo no compara nada.
    expect(chips.length).toBe(3)

    for (const chip of chips) {
      const antes = (a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length
      chip.quitar()
      expect((a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length, `el chip "${chip.etiqueta}" no reseteó la página`).toBe(antes + 1)
    }
  })

  it("quitar Empresa limpia también el Área: un área es de UNA empresa", () => {
    // Dejarla puesta al soltar la empresa deja la grilla en cero sin que nada lo explique.
    const a = args({ empresaFiltro: "e1", areaFiltro: "a1" })
    chipsDeCampos(construirCampos(a)).find((c) => c.clave === "Empresa")!.quitar()
    expect(a.setEmpresaFiltro).toHaveBeenCalledWith("")
    expect(a.setAreaFiltro).toHaveBeenCalledWith("")
  })

  it("qué queda atrás de 'Más filtros': sólo Área, que es el recorte a otra entidad", () => {
    const campos = construirCampos(args())
    expect(campos.filter((c) => c.avanzado).map((c) => c.label)).toEqual(["Área"])
    expect(campos.filter((c) => !c.avanzado).map((c) => c.label)).toEqual(["Empresa", "Estado"])
  })

  it("con una empresa elegida en el sidebar, el filtro de Empresa no se ofrece", () => {
    expect(construirCampos(args({ empresaActivaId: "e1" })).map((c) => c.label)).toEqual(["Estado", "Área"])
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

function grilla(props: Partial<Parameters<typeof ProyectosGrid>[0]> = {}) {
  return renderToStaticMarkup(
    <ProyectosGrid
      proyectos={[]} loading={false} error={null} canWrite
      onEdit={() => {}} onRetry={() => {}}
      chips={[chip("Empresa", "Karstec"), chip("Estado", "Pausado")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos usa los valores reales", () => {
  it("🔴 la frase nombra la empresa como sujeto y el resto como condiciones", () => {
    // Antes decía "No hay proyectos registrados" con tres filtros puestos: verdadero, inútil y
    // sobre un padrón cargado, directamente engañoso.
    const html = grilla()
    expect(html).toContain("Karstec no tiene proyectos con estado Pausado.")
    expect(html).not.toContain("No hay proyectos registrados")
  })

  it("ofrece quitar el ÚLTIMO chip y limpiar todo, sin ejecutar ninguna de las dos", () => {
    const html = grilla()
    expect(html).toContain("Quitar estado: Pausado")
    expect(html).not.toContain("Quitar empresa")
    expect(html).toContain("Limpiar todo")
  })

  it("sin filtros es la otra pantalla: 'todavía no hay', y sin nada que quitar", () => {
    const html = grilla({ chips: [], accionVacio: <button>Crear el primero</button> })
    expect(html).toContain("Todavía no hay proyectos")
    expect(html).toContain("Crear el primero")
    expect(html).not.toContain("Limpiar todo")
  })

  it("durante la carga el esqueleto son tarjetas del mismo alto, con shimmer y no pulse", () => {
    const html = grilla({ loading: true })
    expect(html).toContain("animate-shimmer")
    expect(html).toContain("h-60")
  })
})

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "proyectos", "page.tsx")

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(d) el contador del pie sale de `total`, nunca de proyectos.length", () => {
  it("la página le pasa `total={total}` a <Pagination>", () => {
    /*
     * 🔬 MUTATION CHECK CORRIDO SOBRE ESTE TEST (es el de la tanda): con
     * `total={proyectos.length}` en `proyectos/page.tsx` este bloque rojea nombrando el archivo;
     * con `total={total}` pasa. Es el bug que ya apareció tres veces en el repo y no da error:
     * mientras el listado entre en una página, el número es correcto.
     */
    const jsx = readFileSync(PAGINA, "utf8").match(/<Pagination[\s\S]*?\/>/)
    expect(jsx, "la página dejó de renderizar <Pagination>").not.toBeNull()
    expect(jsx![0]).toContain("total={total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0])).toBe(false)
  })

  it("🔴 el pie va SIEMPRE que haya filas, y NUNCA sobre el esqueleto", () => {
    /*
     * Dos arreglos en una línea. Era `{total > PAGE_SIZE && (` — sin guarda de carga:
     *   · con pocos proyectos y un filtro puesto, la pantalla dejaba de decir cuántos había;
     *   · y mientras cargaba el resultado de un filtro nuevo, la barra seguía dibujada con el
     *     `total` del pedido ANTERIOR, encima del esqueleto. Es el caso que apareció en /vacantes.
     *
     * 🔑 Se mira el código SIN COMENTARIOS: la explicación de por qué se sacó la condición vieja
     * la CONTIENE, y un barrido por texto plano marcaría al archivo ya arreglado.
     */
    const codigo = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(codigo).toContain("!loading && !error && proyectos.length > 0 && (")
    expect(codigo).not.toContain("total > PAGE_SIZE")
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría las dos de arriba.
    expect(sinComentarios("if (total > PAGE_SIZE) {}")).toContain("total > PAGE_SIZE")
  })
})
