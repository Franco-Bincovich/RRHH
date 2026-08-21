import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import {
  construirCamposAsignacionesCap, construirCamposCatalogo,
  type ArgsCamposAsignacionesCap, type ArgsCamposCatalogo,
} from "./_camposCapacitaciones"
import { AsignacionesCapTable } from "./AsignacionesCapTable"
import { CatalogoTabla } from "./CatalogoTabla"

/**
 * Los cuatro puntos del patrón del bloque B sobre /capacitaciones (Formación), que tiene DOS
 * pestañas: el catálogo de cursos y las asignaciones.
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos*`, EL CABLEADO REAL. Con campos inventados el chip
 * llamaría a un `onChange` de mentira y el test pasaría con el cableado roto.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (a) que "solo activos" volviera a ser un checkbox: no produce chip.
 *   · (c) que el vacío volviera a reemplazar la tabla entera.
 *   · (d) que ALGUIEN VOLVIERA A BORRAR el `<Pagination>` de asignaciones — que es el estado en el
 *     que estaba: la pestaña paginaba de a 20 sin barra, y las filas 21+ eran inalcanzables.
 */

const EMPRESAS = [{ id: "e1", nombre: "Karstec" }]
const AREAS = [{ id: "a1", nombre: "Sistemas", empresa_id: "e1" }]
const EMPLEADOS = [{ id: "p1", nombre: "Ana", apellido: "Pérez" }]
const CURSOS = [{ id: "c1", nombre: "Higiene y seguridad" }]

function argsCat(over: Partial<ArgsCamposCatalogo> = {}): ArgsCamposCatalogo {
  return {
    empresaActivaId: null, empresas: EMPRESAS as ArgsCamposCatalogo["empresas"],
    empresaFiltro: "", setEmpresaFiltro: vi.fn(),
    activosFiltro: "", setActivosFiltro: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

function argsAsig(over: Partial<ArgsCamposAsignacionesCap> = {}): ArgsCamposAsignacionesCap {
  return {
    empresaActivaId: null, empresas: EMPRESAS as ArgsCamposAsignacionesCap["empresas"],
    empresaFiltro: "", cambiarEmpresa: vi.fn(),
    areas: AREAS as ArgsCamposAsignacionesCap["areas"], areaFiltro: "", setAreaFiltro: vi.fn(),
    estadoFiltro: "", setEstadoFiltro: vi.fn(),
    empleados: EMPLEADOS as ArgsCamposAsignacionesCap["empleados"], empleadoFiltro: "", setEmpleadoFiltro: vi.fn(),
    capacitaciones: CURSOS as ArgsCamposAsignacionesCap["capacitaciones"], capacitacionFiltro: "", setCapacitacionFiltro: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

describe("(a) los chips muestran el label legible, no el value crudo", () => {
  it("🔴 Catálogo: 'solo activos' PRODUCE CHIP — el checkbox de antes no producía ninguno", () => {
    const [chip] = chipsDeCampos(construirCamposCatalogo(argsCat({ activosFiltro: "todos" })))
    expect(chip.etiqueta).toBe("Estado")
    expect(chip.valor).toBe("Activos e inactivos")
  })

  it("Catálogo: el default —sólo activos— NO produce chip (es el default del backend)", () => {
    // Contracara: sin esto, un `chipsDeCampos` que devolviera siempre un chip pasaría el de arriba.
    expect(chipsDeCampos(construirCamposCatalogo(argsCat()))).toEqual([])
  })

  it("Asignaciones: Estado dice 'En curso' y la Formación dice su nombre", () => {
    const chips = chipsDeCampos(construirCamposAsignacionesCap(argsAsig({ estadoFiltro: "en_curso", capacitacionFiltro: "c1" })))
    expect(chips.find((c) => c.clave === "Estado")!.valor).toBe("En curso")
    expect(chips.find((c) => c.clave === "Formación")!.valor).toBe("Higiene y seguridad")
  })
})

describe("(b) quitar un chip quita ESE filtro, no los otros, y resetea a página 1", () => {
  it("Asignaciones: quitar Estado no toca Área ni Colaborador", () => {
    const a = argsAsig({ estadoFiltro: "pendiente", areaFiltro: "a1", empleadoFiltro: "p1" })
    chipsDeCampos(construirCamposAsignacionesCap(a)).find((c) => c.clave === "Estado")!.quitar()
    expect(a.setEstadoFiltro).toHaveBeenCalledWith("")
    expect(a.onFiltroChange).toHaveBeenCalled()
    expect(a.setAreaFiltro).not.toHaveBeenCalled()
    expect(a.setEmpleadoFiltro).not.toHaveBeenCalled()
  })

  it("Asignaciones: vale para TODOS los filtros con chip", () => {
    const a = argsAsig({
      empresaFiltro: "e1", areaFiltro: "a1", estadoFiltro: "pendiente",
      empleadoFiltro: "p1", capacitacionFiltro: "c1",
    })
    const chips = chipsDeCampos(construirCamposAsignacionesCap(a))
    // Guarda contra el falso verde: sin chips, el for de abajo no compara nada.
    expect(chips.length).toBe(5)
    for (const chip of chips) {
      const antes = (a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length
      chip.quitar()
      expect((a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length, `el chip "${chip.etiqueta}" no reseteó la página`).toBe(antes + 1)
    }
  })

  it("qué queda atrás de 'Más filtros' en cada pestaña, y por qué", () => {
    /*
     * Asignaciones: la pregunta diaria es "¿quién debe qué?", así que Empresa, Área y Estado
     * quedan a la vista; Colaborador (una persona) y Formación (un curso) son consultas puntuales.
     * Catálogo: dos controles —y uno sólo existe en consolidado—, así que esconder alguno dejaría
     * la fila superior sin ningún control a la vista.
     */
    expect(construirCamposAsignacionesCap(argsAsig()).filter((c) => c.avanzado).map((c) => c.label))
      .toEqual(["Colaborador", "Formación"])
    expect(construirCamposCatalogo(argsCat()).filter((c) => c.avanzado)).toEqual([])
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

function tablaCatalogo(props: Partial<Parameters<typeof CatalogoTabla>[0]> = {}) {
  return renderToStaticMarkup(
    <CatalogoTabla
      capacitaciones={[]} loading={false} error={false} onReintentar={() => {}}
      canWrite deletingId={null} onEditar={() => {}} onEliminar={() => {}} mostrarEmpresa
      chips={[chip("Estado", "Activos e inactivos")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos mantiene el encabezado y usa los valores reales", () => {
  it("Catálogo: las columnas siguen ahí y la frase nombra el filtro", () => {
    const html = tablaCatalogo()
    for (const columna of ["Nombre", "Categoría", "Duración", "Empresa", "Obligatoria", "Estado"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
    expect(html).toContain('colSpan="7"')
    expect(html).toContain("No hay formaciones con estado Activos e inactivos.")
  })

  it("Catálogo: sin filtros ofrece crear el primero, en femenino", () => {
    const html = tablaCatalogo({ chips: [], accionVacio: <button>Nuevo curso</button> })
    expect(html).toContain("Todavía no hay formaciones")
    // 🔴 El género: "la primera", no "el primero". Es el arreglo del bloque 0.
    expect(html).toContain("Cuando se cargue la primera va a aparecer acá")
    expect(html).toContain("Nuevo curso")
  })

  it("Catálogo: el esqueleto tiene la misma cantidad de columnas, con y sin permiso", () => {
    const cargando = tablaCatalogo({ loading: true })
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(7)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 7)
    expect(cargando).toContain("animate-shimmer")
    const sinPermiso = tablaCatalogo({ loading: true, canWrite: false })
    expect((sinPermiso.match(/<th[ >]/g) ?? []).length).toBe(6)
  })

  it("Asignaciones: el encabezado se queda y la frase nombra el filtro", () => {
    const html = renderToStaticMarkup(
      <AsignacionesCapTable
        asignaciones={[]} loading={false} error={false} canWrite mostrarEmpresa
        deletingId={null} onReload={() => {}} onEditarEstado={() => {}} onEliminar={() => {}}
        chips={[chip("Estado", "Pendiente")]} onLimpiarTodo={() => {}}
      />,
    )
    expect(html).toContain("<thead")
    expect(html).toContain("No hay asignaciones con estado Pendiente.")
  })
})

describe("🔴 los badges no son azules", () => {
  it("'Obligatoria: Sí' usa el par de ATENCIÓN, no `bg-primary`", () => {
    const html = tablaCatalogo({
      chips: [], capacitaciones: [{
        id: "c1", nombre: "Higiene", categoria: null, duracion_horas: null,
        empresa_nombre: "Karstec", obligatoria: true, activo: true,
      } as Parameters<typeof CatalogoTabla>[0]["capacitaciones"][number]],
    })
    // Ser obligatorio no es un logro: es una condición que genera trabajo.
    expect(html).toContain("bg-warning-wash")
    expect(html).not.toContain("bg-primary")
  })
})

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(d) el contador del pie sale de `total`", () => {
  it("🔴 ASIGNACIONES TIENE PIE — antes NO tenía, y eso hacía inalcanzables las filas 21+", () => {
    /*
     * La pestaña ya llevaba `page` y `total` y ya pedía de a 20 al backend, pero **nunca
     * renderizaba `<Pagination>`**: el import estaba puesto y sin usar. Con más de 20
     * asignaciones cargadas, las que sobraban no se podían ver desde la UI y no había ninguna
     * señal de que existieran. Este test existe para que no vuelva a desaparecer.
     */
    const src = readFileSync(path.resolve(__dirname, "AsignacionesTab.tsx"), "utf8")
    const jsx = src.match(/<Pagination[\s\S]*?\/>/)
    expect(jsx, "la pestaña de asignaciones volvió a quedarse sin barra de paginación").not.toBeNull()
    expect(jsx![0]).toContain("total={total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0])).toBe(false)
    expect(sinComentarios(src)).toContain("!loading && !error && asignaciones.length > 0 && (")
  })

  it("el CATÁLOGO no tiene pie, y eso es correcto: su endpoint no pagina", () => {
    // `GET /api/capacitaciones` no acepta `page` ni `page_size`. Derivar un pie del array traído
    // es el bug que `paginacionTotales.test.ts` persigue.
    const src = readFileSync(path.resolve(__dirname, "CatalogoTab.tsx"), "utf8")
    expect(src).not.toContain("<Pagination")
    // Contracara: el archivo leído es el que se cree.
    expect(src).toContain("<CatalogoTabla")
  })
})
