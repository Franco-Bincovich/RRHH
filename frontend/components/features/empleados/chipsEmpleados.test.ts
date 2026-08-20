import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"

import { construirCampos, type ArgsCampos } from "./_camposEmpleados"

/**
 * Los chips de /empleados contra el cableado REAL de la pantalla.
 *
 * 🔴 POR QUÉ CONTRA `construirCampos` Y NO CONTRA CAMPOS INVENTADOS. Lo que se prueba acá no es
 * la derivación del chip —eso vive en `components/ui/filtrosChips.test.tsx`— sino que quitar un
 * chip dispare **lo que la pantalla cuelga de ese filtro**: el reseteo a página 1 (invariante 4
 * del bloque B) y, en Empresa, el limpiado del Área. Con campos de mentira, el chip llamaría a un
 * `onChange` de mentira y el test pasaría con el cableado roto — que es exactamente el falso verde
 * que CLAUDE.md documenta ("un test solo prueba lo que el fake puede desmentir").
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDA FALLAR? Que `chipsDeCampos` llamara al `onChange`
 * del campo por otro camino que no fuera el del control (por ejemplo, un setter propio): ahí
 * `onFiltroChange` no se llama y el usuario queda en la página 4 de un listado que ahora tiene una.
 */

const EMPRESAS = [{ id: "e1", nombre: "Karstec" }, { id: "e2", nombre: "Dosuba" }]
const AREAS = [{ id: "a1", nombre: "Sistemas", empresa_id: "e1" }]

function args(over: Partial<ArgsCampos> = {}): ArgsCampos {
  return {
    search: "", setSearch: vi.fn(),
    empresaActivaId: null, empresas: EMPRESAS as ArgsCampos["empresas"],
    empresaFiltro: "", setEmpresaFiltro: vi.fn(),
    areas: AREAS as ArgsCampos["areas"], areaFiltro: "", setAreaFiltro: vi.fn(),
    estadoFiltro: "", setEstadoFiltro: vi.fn(),
    liderFiltro: "", setLiderFiltro: vi.fn(),
    sinManagerFiltro: "", setSinManagerFiltro: vi.fn(),
    proyectos: [], proyectoFiltro: "", setProyectoFiltro: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

describe("(c) quitar un chip resetea a página 1", () => {
  it("el chip de Estado dispara onFiltroChange, que es el () => setPage(1) de la página", () => {
    const a = args({ estadoFiltro: "preingreso" })
    const chips = chipsDeCampos(construirCampos(a))

    chips.find((c) => c.clave === "Estado")!.quitar()

    expect(a.setEstadoFiltro).toHaveBeenCalledWith("")
    expect(a.onFiltroChange).toHaveBeenCalled()
  })

  it("vale para TODOS los filtros con chip, no sólo para Estado", () => {
    // Un filtro nuevo que se olvide del reset entra por acá sin tocar el test.
    const a = args({ estadoFiltro: "activo", empresaFiltro: "e1", areaFiltro: "a1", liderFiltro: "si", sinManagerFiltro: "si" })
    const chips = chipsDeCampos(construirCampos(a))
    expect(chips.length).toBeGreaterThanOrEqual(5)

    for (const chip of chips) {
      const antes = (a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length
      chip.quitar()
      expect((a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length, `el chip "${chip.etiqueta}" no reseteó la página`).toBe(antes + 1)
    }
  })

  it("🔬 la excepción DECLARADA: el buscador resetea por el debounce, no por su onChange", () => {
    // `setSearch` sólo mueve el texto; el reset viaja con el commit del debounce, en el hook. Es
    // por eso que el barrido de arriba corre sobre los chips de los SELECT: el de Buscar llamaría
    // a `onFiltroChange` 350ms después y no en el mismo tick.
    const a = args({ search: "juan" })
    const chip = chipsDeCampos(construirCampos(a)).find((c) => c.clave === "Buscar")!

    chip.quitar()

    expect(a.setSearch).toHaveBeenCalledWith("")
    expect(a.onFiltroChange).not.toHaveBeenCalled()
  })
})

describe("quitar un chip hereda los efectos propios del filtro", () => {
  it("quitar Empresa limpia también el Área, igual que elegir 'Todas las empresas'", () => {
    // Un área es de UNA empresa: dejarla puesta al soltar la empresa deja el listado en cero sin
    // que nada lo explique. El chip no reimplementa nada — llama al mismo onChange del control.
    const a = args({ empresaFiltro: "e1", areaFiltro: "a1" })
    const chips = chipsDeCampos(construirCampos(a))

    chips.find((c) => c.clave === "Empresa")!.quitar()

    expect(a.setEmpresaFiltro).toHaveBeenCalledWith("")
    expect(a.setAreaFiltro).toHaveBeenCalledWith("")
  })

  it("el chip de Empresa muestra el nombre, no el uuid", () => {
    const chips = chipsDeCampos(construirCampos(args({ empresaFiltro: "e1" })))
    expect(chips.find((c) => c.clave === "Empresa")!.valor).toBe("Karstec")
  })
})

describe("qué queda atrás de 'Más filtros'", () => {
  it("Liderazgo, Superior y Proyecto son avanzados; Buscar, Empresa, Área y Estado no", () => {
    const campos = construirCampos(args({ proyectos: [{ id: "p1", nombre: "Karstec" }] as ArgsCampos["proyectos"] }))
    const avanzados = campos.filter((c) => c.avanzado).map((c) => c.label)
    const visibles = campos.filter((c) => !c.avanzado).map((c) => c.label)

    expect(avanzados).toEqual(["Liderazgo", "Superior", "Proyecto"])
    expect(visibles).toEqual(["Buscar", "Empresa", "Área", "Estado"])
  })
})
