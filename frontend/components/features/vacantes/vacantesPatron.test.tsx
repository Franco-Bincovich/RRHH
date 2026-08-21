import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import { construirCampos, type ArgsCamposVacantes } from "./_camposVacantes"
import { ESTADO_LABEL } from "./_grillaVacantes"
import { VacantesTable } from "./VacantesTable"

/**
 * Los cuatro puntos del patrón del bloque B sobre /vacantes: (a) el chip dice el label legible,
 * (b) quitar uno quita ESE filtro y resetea la página, (c) el vacío conserva el encabezado y habla
 * con los valores reales, (d) el pie sale de `total`.
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos`, EL CABLEADO REAL. Con campos inventados el chip
 * llamaría a un `onChange` de mentira y el test pasaría con el cableado roto.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (a) que las opciones del select dejaran de salir de `ESTADO_LABEL`: ahí el chip puede decir
 *     "en_proceso" y la fila "En proceso" sin que nada falle.
 *   · (b) que un `onChange` se olvidara de `onFiltroChange`.
 *   · (c) que la tabla volviera a delegar sus estados en la página, con el esqueleto de barras
 *     sueltas que tenía: desaparece `<thead>` y las columnas se acomodan al llegar los datos.
 *   · (d) que la página le pasara `vacantes.length` a `<Pagination>`.
 */

const EMPRESAS = [{ id: "e1", nombre: "Karstec" }, { id: "e2", nombre: "Dosuba" }]

function args(over: Partial<ArgsCamposVacantes> = {}): ArgsCamposVacantes {
  return {
    empresaActivaId: null, empresas: EMPRESAS as ArgsCamposVacantes["empresas"],
    empresaFiltro: "", setEmpresaFiltro: vi.fn(),
    estadoFiltro: "", setEstadoFiltro: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

describe("(a) los chips muestran el label legible, no el value crudo", () => {
  it("Empresa dice el nombre y Estado dice 'En proceso', no 'en_proceso'", () => {
    const chips = chipsDeCampos(construirCampos(args({ empresaFiltro: "e1", estadoFiltro: "en_proceso" })))
    expect(chips.find((c) => c.clave === "Empresa")!.valor).toBe("Karstec")
    expect(chips.find((c) => c.clave === "Estado")!.valor).toBe("En proceso")
  })

  it("las opciones del select son EXACTAMENTE los cuatro estados, con los textos del export", () => {
    // Salen de `ESTADO_LABEL`, el mismo mapa que pinta el badge: dos catálogos del mismo dato
    // divergen, y el que solo se mira con un filtro puesto diverge sin que nadie lo vea.
    const estado = construirCampos(args()).find((c) => c.label === "Estado")!
    expect(estado.tipo).toBe("select")
    expect(estado.tipo === "select" && estado.opciones.map((o) => o.value))
      .toEqual(Object.keys(ESTADO_LABEL))
  })
})

describe("(b) quitar un chip quita ESE filtro, no los otros, y resetea a página 1", () => {
  it("quitar Estado no toca Empresa", () => {
    const a = args({ estadoFiltro: "cerrada", empresaFiltro: "e1" })
    chipsDeCampos(construirCampos(a)).find((c) => c.clave === "Estado")!.quitar()

    expect(a.setEstadoFiltro).toHaveBeenCalledWith("")
    expect(a.onFiltroChange).toHaveBeenCalled()
    expect(a.setEmpresaFiltro).not.toHaveBeenCalled()
  })

  it("vale para los dos filtros, no sólo para Estado", () => {
    const a = args({ estadoFiltro: "cerrada", empresaFiltro: "e1" })
    const chips = chipsDeCampos(construirCampos(a))
    // Guarda contra el falso verde: sin chips, el for de abajo no compara nada.
    expect(chips.length).toBe(2)

    for (const chip of chips) {
      const antes = (a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length
      chip.quitar()
      expect((a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length, `el chip "${chip.etiqueta}" no reseteó la página`).toBe(antes + 1)
    }
  })

  it("con una empresa elegida en el sidebar, el filtro de Empresa no se ofrece", () => {
    // El listado ya viene acotado por el header: el select no podría cambiar nada.
    const campos = construirCampos(args({ empresaActivaId: "e1" }))
    expect(campos.map((c) => c.label)).toEqual(["Estado"])
  })

  it("ninguno de los dos filtros es avanzado: con dos, esconder uno no compra nada", () => {
    expect(construirCampos(args()).filter((c) => c.avanzado)).toEqual([])
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

function tabla(props: Partial<Parameters<typeof VacantesTable>[0]> = {}) {
  return renderToStaticMarkup(
    <VacantesTable
      vacantes={[]} loading={false} error={false} mostrarEmpresa
      onRetry={() => {}} onAbrir={() => {}}
      chips={[chip("Empresa", "Karstec"), chip("Estado", "Cerrada")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos mantiene el encabezado y usa los valores reales", () => {
  it("las columnas siguen ahí y el vacío es una fila de la tabla", () => {
    const html = tabla()
    for (const columna of ["Título", "Empresa", "Área", "Estado", "Fecha de apertura"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
    expect(html).toContain('colSpan="6"')
  })

  it("la frase nombra la empresa como sujeto y el resto como condiciones", () => {
    expect(tabla()).toContain("Karstec no tiene vacantes con estado Cerrada.")
  })

  it("sin filtros no ofrece quitar nada: ofrece crear la primera", () => {
    const html = tabla({ chips: [], accionVacio: <button>Crear la primera</button> })
    expect(html).toContain("Todavía no hay vacantes")
    expect(html).toContain("Crear la primera")
    expect(html).not.toContain("Limpiar todo")
  })

  it("el esqueleto tiene la misma cantidad de columnas que la tabla, en las dos variantes", () => {
    const cargando = tabla({ loading: true })
    expect(cargando).toContain("<thead")
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(6)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 6)
    expect(cargando).toContain("animate-shimmer")
    const sinEmpresa = tabla({ loading: true, mostrarEmpresa: false })
    expect((sinEmpresa.match(/<th[ >]/g) ?? []).length).toBe(5)
    expect((sinEmpresa.match(/<td[ >]/g) ?? []).length).toBe(8 * 5)
  })
})

describe("🔴 ningún badge de estado es azul", () => {
  it("en_proceso dejó de ser `bg-primary` y usa un par semántico", () => {
    const html = tabla({
      chips: [], vacantes: [{
        id: "1", titulo: "Analista", estado: "en_proceso", created_at: "2026-01-05",
      } as Parameters<typeof VacantesTable>[0]["vacantes"][number]],
    })
    expect(html).toContain("En proceso")
    expect(html).not.toContain("bg-primary")
  })
})

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "vacantes", "page.tsx")

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(d) el contador del pie sale de `total`, nunca de vacantes.length", () => {
  it("la página le pasa `total={total}` a <Pagination>", () => {
    const jsx = readFileSync(PAGINA, "utf8").match(/<Pagination[\s\S]*?\/>/)
    expect(jsx, "la página dejó de renderizar <Pagination>").not.toBeNull()
    expect(jsx![0]).toContain("total={total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0])).toBe(false)
  })

  it("🔴 el pie va SIEMPRE que haya filas, y sólo después de cargar", () => {
    // Antes era `total > PAGE_SIZE` y además SIN esperar a que terminara la carga: la barra se
    // dibujaba sobre el esqueleto con el total del pedido anterior.
    const codigo = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(codigo).toContain("!loading && !error && vacantes.length > 0 && (")
    expect(codigo).not.toContain("total > PAGE_SIZE")
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría las dos de arriba.
    expect(sinComentarios("if (total > PAGE_SIZE) {}")).toContain("total > PAGE_SIZE")
  })
})
