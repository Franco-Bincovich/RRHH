import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import { construirCampos, type ArgsCamposAusencias } from "./_camposAusencias"
import { AusenciasTable } from "./AusenciasTable"

/**
 * Los cuatro puntos del patrón del bloque B sobre /ausencias: (a) el chip dice el label legible,
 * (b) quitar uno quita ESE filtro y resetea la página, (c) el vacío conserva el encabezado y
 * habla con los valores reales, (d) el pie sale de `total`.
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos`, EL CABLEADO REAL DE LA PANTALLA, no contra campos
 * inventados. Con campos de mentira el chip llamaría a un `onChange` de mentira y el test pasaría
 * con el cableado roto — el falso verde que CLAUDE.md documenta.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (a) que el chip mostrara `campo.value` (el uuid) en vez de buscarlo en `opciones`.
 *   · (b) que un `onChange` se olvidara de `onFiltroChange` — el usuario queda en la página 4 de
 *     un listado que ahora tiene una.
 *   · (c) que la tabla volviera a reemplazarse entera por un `<EmptyState>`: desaparece `<thead>`.
 *   · (d) que la página le pasara `items.length` a `<Pagination>`: el pie diría "de 20" con 400
 *     filas cargadas y no hay ningún error visible.
 *
 * ALCANCE, sin disimular: vitest corre sin jsdom, así que (c) se verifica sobre el MARKUP y los
 * handlers de (b) se invocan a mano; (d) se verifica leyendo el JSX de la página, que es donde
 * vive la decisión.
 */

const EMPRESAS = [{ id: "e1", nombre: "Karstec" }, { id: "e2", nombre: "Dosuba" }]
const AREAS = [{ id: "a1", nombre: "Sistemas", empresa_id: "e1" }]
const TIPOS = [{ id: "t1", nombre: "Enfermedad" }]
const EMPLEADOS = [{ id: "p1", nombre: "Ana", apellido: "Pérez" }]

function args(over: Partial<ArgsCamposAusencias> = {}): ArgsCamposAusencias {
  return {
    empresaActivaId: null, empresas: EMPRESAS as ArgsCamposAusencias["empresas"],
    empresaFiltro: "", setEmpresaFiltro: vi.fn(),
    areas: AREAS as ArgsCamposAusencias["areas"], areaFiltro: "", setAreaFiltro: vi.fn(),
    empleadosSel: EMPLEADOS as ArgsCamposAusencias["empleadosSel"], empleadoFiltro: "", setEmpleadoFiltro: vi.fn(),
    tipos: TIPOS as ArgsCamposAusencias["tipos"], tipoFiltro: "", setTipoFiltro: vi.fn(),
    rango: { desde: "", hasta: "" }, setRango: vi.fn(),
    proyectos: [], proyectoFiltro: "", setProyectoFiltro: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

describe("(a) los chips muestran el label legible, no el value crudo", () => {
  it("Empresa, Área y Tipo dicen el nombre y no el uuid", () => {
    const chips = chipsDeCampos(construirCampos(args({ empresaFiltro: "e1", areaFiltro: "a1", tipoFiltro: "t1" })))
    expect(chips.find((c) => c.clave === "Empresa")!.valor).toBe("Karstec")
    expect(chips.find((c) => c.clave === "Área")!.valor).toBe("Sistemas")
    expect(chips.find((c) => c.clave === "Tipo")!.valor).toBe("Enfermedad")
  })

  it("el Período se lee en formato local y con los rangos abiertos escritos como tales", () => {
    const [chip] = chipsDeCampos(construirCampos(args({ rango: { desde: "2026-03-01", hasta: "2026-03-31" } })))
    expect(chip.valor).toBe("01/03/2026 – 31/03/2026")
    const [abierto] = chipsDeCampos(construirCampos(args({ rango: { desde: "2026-03-01", hasta: "" } })))
    expect(abierto.valor).toBe("desde 01/03/2026")
  })
})

describe("(b) quitar un chip quita ESE filtro, no los otros, y resetea a página 1", () => {
  it("el chip de Tipo llama a su setter con vacío y dispara el reset", () => {
    const a = args({ tipoFiltro: "t1", areaFiltro: "a1" })
    chipsDeCampos(construirCampos(a)).find((c) => c.clave === "Tipo")!.quitar()

    expect(a.setTipoFiltro).toHaveBeenCalledWith("")
    expect(a.onFiltroChange).toHaveBeenCalled()
    // Y no tocó a los demás: el chip llama al MISMO onChange del control, nada más.
    expect(a.setAreaFiltro).not.toHaveBeenCalled()
    expect(a.setEmpleadoFiltro).not.toHaveBeenCalled()
  })

  it("vale para TODOS los filtros con chip, no sólo para Tipo", () => {
    // Un filtro nuevo que se olvide del reset entra por acá sin tocar el test.
    const a = args({
      empresaFiltro: "e1", areaFiltro: "a1", tipoFiltro: "t1", empleadoFiltro: "p1",
      rango: { desde: "2026-03-01", hasta: "" },
      proyectos: [{ id: "pr1", nombre: "Karstec" }] as ArgsCamposAusencias["proyectos"], proyectoFiltro: "pr1",
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

  it("quitar Empresa limpia también Área y Colaborador, igual que elegir 'Todas las empresas'", () => {
    // Un área y un colaborador son de UNA empresa: dejarlos puestos al soltarla deja el listado
    // en cero sin que nada lo explique.
    const a = args({ empresaFiltro: "e1", areaFiltro: "a1", empleadoFiltro: "p1" })
    chipsDeCampos(construirCampos(a)).find((c) => c.clave === "Empresa")!.quitar()

    expect(a.setEmpresaFiltro).toHaveBeenCalledWith("")
    expect(a.setAreaFiltro).toHaveBeenCalledWith("")
    expect(a.setEmpleadoFiltro).toHaveBeenCalledWith("")
  })

  it("qué queda atrás de 'Más filtros': Colaborador y Proyecto, y nada más", () => {
    const campos = construirCampos(args({ proyectos: [{ id: "pr1", nombre: "Karstec" }] as ArgsCamposAusencias["proyectos"] }))
    expect(campos.filter((c) => c.avanzado).map((c) => c.label)).toEqual(["Colaborador", "Proyecto"])
    expect(campos.filter((c) => !c.avanzado).map((c) => c.label)).toEqual(["Empresa", "Área", "Tipo", "Período"])
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

function tabla(props: Partial<Parameters<typeof AusenciasTable>[0]> = {}) {
  return renderToStaticMarkup(
    <AusenciasTable
      items={[]} loading={false} error={false} showEmpresa canWrite deletingId={null}
      onRetry={() => {}} onEdit={() => {}} onDelete={() => {}} onDocs={() => {}}
      chips={[chip("Empresa", "Karstec"), chip("Tipo", "Enfermedad")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos mantiene el encabezado y usa los valores reales", () => {
  it("las columnas siguen ahí y el vacío es una fila de la tabla, no un bloque que la reemplaza", () => {
    const html = tabla()
    for (const columna of ["Colaborador", "Área", "Empresa", "Tipo", "Desde", "Hasta", "Días", "Justificada", "Motivo"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
    expect(html).toContain('colSpan="10"')
  })

  it("la frase nombra la empresa como sujeto y el resto como condiciones", () => {
    expect(tabla()).toContain("Karstec no tiene ausencias con tipo Enfermedad.")
  })

  it("sin filtros no ofrece quitar nada: ofrece registrar la primera", () => {
    const html = tabla({ chips: [], accionVacio: <button>Registrar la primera</button> })
    expect(html).toContain("Todavía no hay ausencias")
    expect(html).toContain("Registrar la primera")
    expect(html).not.toContain("Limpiar todo")
  })

  it("y el encabezado también está durante la carga: la forma no cambia nunca", () => {
    const cargando = tabla({ loading: true })
    expect(cargando).toContain("<thead")
    // El esqueleto tiene la MISMA cantidad de columnas que la tabla: 8 filas × 10 columnas.
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(10)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 10)
    expect(cargando).toContain("animate-shimmer")
  })

  it("y con el sidebar en una empresa, la columna Empresa se va del encabezado Y del esqueleto", () => {
    // La grilla es UNA sola lista: si el esqueleto declarara sus columnas aparte, esta variante
    // es la que las desalinea.
    const cargando = tabla({ loading: true, showEmpresa: false })
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(9)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 9)
  })
})

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "ausencias", "page.tsx")

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows, cada
 *  línea termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea
 *  nunca y la función devolvería el código intacto — verde en la Mac, rojo en la Lenovo. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(d) el contador del pie sale de `total`, nunca de items.length", () => {
  it("la página le pasa `total={total}` a <Pagination>", () => {
    /*
     * 🔬 MUTATION CHECK CORRIDO SOBRE ESTE TEST (es el de la tanda): con
     * `total={items.length}` en `ausencias/page.tsx` este bloque rojea nombrando el archivo;
     * con `total={total}` pasa. Es el bug que ya apareció tres veces en el repo y no da error:
     * mientras el listado entre en una página, el número es correcto.
     */
    const jsx = readFileSync(PAGINA, "utf8").match(/<Pagination[\s\S]*?\/>/)
    expect(jsx, "la página dejó de renderizar <Pagination>").not.toBeNull()
    expect(jsx![0]).toContain("total={total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0])).toBe(false)
  })

  it("🔴 el pie va SIEMPRE que haya filas, no sólo con más de una página", () => {
    /*
     * Era `total > PAGE_SIZE`: con pocos registros y un filtro puesto, la pantalla dejaba de
     * decir cuántos resultados había justo cuando el filtro es lo que hay que entender.
     *
     * 🔑 SE MIRA EL CÓDIGO SIN COMENTARIOS, y hace falta: el comentario que explica por qué se
     * sacó la condición vieja CONTIENE la condición vieja, así que un barrido por texto plano
     * marcaba como culpable justo al archivo ya arreglado — y el "arreglo" natural de ese falso
     * positivo es borrar la explicación. Misma trampa que `paginacionTotales.test.ts` documenta.
     */
    const codigo = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(codigo).toContain("items.length > 0 && (")
    expect(codigo).not.toContain("total > PAGE_SIZE")
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría las dos de arriba.
    expect(sinComentarios("// total > PAGE_SIZE\nconst x = 1")).not.toContain("total > PAGE_SIZE")
    expect(sinComentarios("if (total > PAGE_SIZE) {}")).toContain("total > PAGE_SIZE")
  })
})
