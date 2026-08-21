import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import { construirCampos, type ArgsCamposVacaciones } from "./_camposVacaciones"
import { VacacionesTable } from "./VacacionesTable"

/**
 * Los cuatro puntos del patrón del bloque B sobre /vacaciones: (a) el chip dice el label legible,
 * (b) quitar uno quita ESE filtro y resetea la página, (c) el vacío conserva el encabezado y habla
 * con los valores reales, (d) el pie sale de `total`.
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos`, EL CABLEADO REAL DE LA PANTALLA. Con campos
 * inventados el chip llamaría a un `onChange` de mentira y el test pasaría con el cableado roto.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR? Lo mismo que en /ausencias, más una
 * propia de esta pantalla: que la vista LISTA volviera a delegar sus estados en la página. Ahí el
 * vacío deja de poder vivir adentro de la `<Table>` y `<thead>` desaparece de nuevo.
 */

const EMPRESAS = [{ id: "e1", nombre: "Karstec" }, { id: "e2", nombre: "Dosuba" }]
const AREAS = [{ id: "a1", nombre: "Sistemas", empresa_id: "e1" }]
const EMPLEADOS = [{ id: "p1", nombre: "Ana", apellido: "Pérez" }]

function args(over: Partial<ArgsCamposVacaciones> = {}): ArgsCamposVacaciones {
  return {
    empresaActivaId: null, empresas: EMPRESAS as ArgsCamposVacaciones["empresas"],
    empresaFiltro: "", setEmpresaFiltro: vi.fn(),
    areas: AREAS as ArgsCamposVacaciones["areas"], areaFiltro: "", setAreaFiltro: vi.fn(),
    empleadosSel: EMPLEADOS as ArgsCamposVacaciones["empleadosSel"], empleadoFiltro: "", setEmpleadoFiltro: vi.fn(),
    estadoFiltro: "", setEstadoFiltro: vi.fn(),
    rango: { desde: "", hasta: "" }, setRango: vi.fn(),
    proyectos: [], proyectoFiltro: "", setProyectoFiltro: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

describe("(a) los chips muestran el label legible, no el value crudo", () => {
  it("Empresa y Área dicen el nombre; Estado dice 'Planificada' y no 'planificada'", () => {
    const chips = chipsDeCampos(construirCampos(args({ empresaFiltro: "e1", areaFiltro: "a1", estadoFiltro: "planificada" })))
    expect(chips.find((c) => c.clave === "Empresa")!.valor).toBe("Karstec")
    expect(chips.find((c) => c.clave === "Área")!.valor).toBe("Sistemas")
    expect(chips.find((c) => c.clave === "Estado")!.valor).toBe("Planificada")
  })

  it("el Colaborador se lee 'Apellido, Nombre' y no el uuid", () => {
    const chips = chipsDeCampos(construirCampos(args({ empleadoFiltro: "p1" })))
    expect(chips.find((c) => c.clave === "Colaborador")!.valor).toBe("Pérez, Ana")
  })
})

describe("(b) quitar un chip quita ESE filtro, no los otros, y resetea a página 1", () => {
  it("el chip de Estado llama a su setter con vacío y dispara el reset", () => {
    const a = args({ estadoFiltro: "tomada", areaFiltro: "a1" })
    chipsDeCampos(construirCampos(a)).find((c) => c.clave === "Estado")!.quitar()

    expect(a.setEstadoFiltro).toHaveBeenCalledWith("")
    expect(a.onFiltroChange).toHaveBeenCalled()
    expect(a.setAreaFiltro).not.toHaveBeenCalled()
    expect(a.setEmpleadoFiltro).not.toHaveBeenCalled()
  })

  it("vale para TODOS los filtros con chip, no sólo para Estado", () => {
    const a = args({
      empresaFiltro: "e1", areaFiltro: "a1", estadoFiltro: "tomada", empleadoFiltro: "p1",
      rango: { desde: "", hasta: "2026-01-31" },
      proyectos: [{ id: "pr1", nombre: "Karstec" }] as ArgsCamposVacaciones["proyectos"], proyectoFiltro: "pr1",
    })
    const chips = chipsDeCampos(construirCampos(a))
    // Guarda contra el falso verde: sin chips, el for de abajo no compara nada.
    expect(chips.length).toBeGreaterThanOrEqual(6)

    for (const chip of chips) {
      const antes = (a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length
      chip.quitar()
      expect((a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length, `el chip "${chip.etiqueta}" no reseteó la página`).toBe(antes + 1)
    }
  })

  it("quitar Empresa limpia también Área y Colaborador", () => {
    const a = args({ empresaFiltro: "e1", areaFiltro: "a1", empleadoFiltro: "p1" })
    chipsDeCampos(construirCampos(a)).find((c) => c.clave === "Empresa")!.quitar()

    expect(a.setEmpresaFiltro).toHaveBeenCalledWith("")
    expect(a.setAreaFiltro).toHaveBeenCalledWith("")
    expect(a.setEmpleadoFiltro).toHaveBeenCalledWith("")
  })

  it("qué queda atrás de 'Más filtros': Colaborador y Proyecto, y nada más", () => {
    const campos = construirCampos(args({ proyectos: [{ id: "pr1", nombre: "Karstec" }] as ArgsCamposVacaciones["proyectos"] }))
    expect(campos.filter((c) => c.avanzado).map((c) => c.label)).toEqual(["Colaborador", "Proyecto"])
    expect(campos.filter((c) => !c.avanzado).map((c) => c.label)).toEqual(["Empresa", "Área", "Estado", "Período"])
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

function tabla(props: Partial<Parameters<typeof VacacionesTable>[0]> = {}) {
  return renderToStaticMarkup(
    <VacacionesTable
      items={[]} loading={false} error={false} canWrite showEmpresa cancelingId={null}
      onRetry={() => {}} onCancel={() => {}} onDocs={() => {}}
      chips={[chip("Empresa", "Karstec"), chip("Estado", "Planificada")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos mantiene el encabezado y usa los valores reales", () => {
  it("las columnas siguen ahí y el vacío es una fila de la tabla", () => {
    const html = tabla()
    for (const columna of ["Colaborador", "Área", "Empresa", "Desde", "Hasta", "Días", "Estado"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
    expect(html).toContain('colSpan="8"')
  })

  it("la frase nombra la empresa como sujeto y el resto como condiciones", () => {
    expect(tabla()).toContain("Karstec no tiene vacaciones con estado Planificada.")
  })

  it("sin filtros no ofrece quitar nada: ofrece registrar las primeras", () => {
    const html = tabla({ chips: [], accionVacio: <button>Registrar las primeras</button> })
    expect(html).toContain("Todavía no hay vacaciones")
    expect(html).toContain("Registrar las primeras")
    expect(html).not.toContain("Limpiar todo")
  })

  it("el esqueleto tiene la misma cantidad de columnas que la tabla, en las dos variantes", () => {
    const cargando = tabla({ loading: true })
    expect(cargando).toContain("<thead")
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(8)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 8)
    expect(cargando).toContain("animate-shimmer")
    // Con el sidebar en una empresa, la columna Empresa se va del encabezado Y del esqueleto.
    const sinEmpresa = tabla({ loading: true, showEmpresa: false })
    expect((sinEmpresa.match(/<th[ >]/g) ?? []).length).toBe(7)
    expect((sinEmpresa.match(/<td[ >]/g) ?? []).length).toBe(8 * 7)
  })
})

describe("🔴 ningún badge de estado es azul", () => {
  it("planificada dejó de ser `bg-primary` y usa un par semántico", () => {
    /*
     * El relleno `--primary` está reservado al chip de filtro (§3). `planificada` venía con
     * `variant="default"`, que ES `bg-primary`: veinte filas de azul compitiendo con el único
     * azul que la pantalla puede tener. Se verifica sobre el markup real de una fila.
     */
    const html = tabla({
      chips: [], items: [{
        id: "1", empleado_nombre: "Ana Pérez", fecha_desde: "2026-01-05", fecha_hasta: "2026-01-15",
        dias: 10, estado: "planificada",
      } as Parameters<typeof VacacionesTable>[0]["items"][number]],
    })
    expect(html).toContain("Planificada")
    expect(html).not.toContain("bg-primary")
  })
})

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "vacaciones", "page.tsx")

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca y
 *  la función devolvería el código intacto — verde en la Mac, rojo en la Lenovo. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(d) el contador del pie sale de `total`, nunca de solicitudes.length", () => {
  it("la página le pasa `total={total}` a <Pagination>", () => {
    const jsx = readFileSync(PAGINA, "utf8").match(/<Pagination[\s\S]*?\/>/)
    expect(jsx, "la página dejó de renderizar <Pagination>").not.toBeNull()
    expect(jsx![0]).toContain("total={total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0])).toBe(false)
  })

  it("🔴 el pie va SIEMPRE que haya filas (y sólo en la vista lista)", () => {
    // Se mira el código SIN COMENTARIOS: el comentario que explica por qué se sacó la condición
    // vieja la CONTIENE, y un barrido por texto plano marcaría al archivo ya arreglado.
    const codigo = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(codigo).toContain('vista === "lista" && solicitudes.length > 0 && (')
    expect(codigo).not.toContain("total > PAGE_SIZE")
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría las dos de arriba.
    expect(sinComentarios("if (total > PAGE_SIZE) {}")).toContain("total > PAGE_SIZE")
  })
})
