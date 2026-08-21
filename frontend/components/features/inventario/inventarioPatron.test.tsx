import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import {
  construirCamposAsignaciones, construirCamposItems,
  type ArgsCamposAsignaciones, type ArgsCamposItems,
} from "./_camposInventario"
import { AsignacionesInvTable } from "./AsignacionesInvTable"
import { ItemsInvTable } from "./ItemsInvTable"

/**
 * Los cuatro puntos del patrón del bloque B sobre /inventario, que tiene **DOS pestañas** y por
 * eso las cubre a las dos: los avanzados son DISTINTOS en cada una y ese es justamente el punto
 * del criterio ("no por posición").
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos*`, EL CABLEADO REAL. Con campos inventados el chip
 * llamaría a un `onChange` de mentira y el test pasaría con el cableado roto.
 */

const EMPRESAS = [{ id: "e1", nombre: "Karstec" }, { id: "e2", nombre: "Dosuba" }]
const AREAS = [{ id: "a1", nombre: "Sistemas", empresa_id: "e1" }]
const EMPLEADOS = [{ id: "p1", nombre: "Ana", apellido: "Pérez" }]

function argsItems(over: Partial<ArgsCamposItems> = {}): ArgsCamposItems {
  return {
    empresaActivaId: null, empresas: EMPRESAS as ArgsCamposItems["empresas"],
    empresaFiltro: "", cambiarEmpresa: vi.fn(),
    estadoFiltro: "", setEstadoFiltro: vi.fn(),
    areas: AREAS as ArgsCamposItems["areas"], areaFiltro: "", setAreaFiltro: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

function argsAsig(over: Partial<ArgsCamposAsignaciones> = {}): ArgsCamposAsignaciones {
  return {
    empresaActivaId: null, empresas: EMPRESAS as ArgsCamposAsignaciones["empresas"],
    empresaFiltro: "", cambiarEmpresa: vi.fn(),
    areas: AREAS as ArgsCamposAsignaciones["areas"], areaFiltro: "", setAreaFiltro: vi.fn(),
    empleados: EMPLEADOS as ArgsCamposAsignaciones["empleados"], empleadoFiltro: "", setEmpleadoFiltro: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

describe("(a) los chips muestran el label legible, no el value crudo", () => {
  it("Ítems: Estado dice 'En reparación' y no 'en_reparacion'", () => {
    const chips = chipsDeCampos(construirCamposItems(argsItems({ estadoFiltro: "en_reparacion", empresaFiltro: "e1" })))
    expect(chips.find((c) => c.clave === "Estado")!.valor).toBe("En reparación")
    expect(chips.find((c) => c.clave === "Empresa")!.valor).toBe("Karstec")
  })

  it("Asignaciones: el Colaborador se lee 'Apellido, Nombre' y no el uuid", () => {
    const chips = chipsDeCampos(construirCamposAsignaciones(argsAsig({ empleadoFiltro: "p1" })))
    expect(chips.find((c) => c.clave === "Colaborador")!.valor).toBe("Pérez, Ana")
  })
})

describe("(b) quitar un chip quita ESE filtro, no los otros, y resetea a página 1", () => {
  it("Ítems: quitar Estado no toca Área", () => {
    const a = argsItems({ estadoFiltro: "asignado", areaFiltro: "a1" })
    chipsDeCampos(construirCamposItems(a)).find((c) => c.clave === "Estado")!.quitar()
    expect(a.setEstadoFiltro).toHaveBeenCalledWith("")
    expect(a.onFiltroChange).toHaveBeenCalled()
    expect(a.setAreaFiltro).not.toHaveBeenCalled()
  })

  it("Ítems: vale para TODOS los filtros con chip", () => {
    const a = argsItems({ empresaFiltro: "e1", estadoFiltro: "asignado", areaFiltro: "a1" })
    const chips = chipsDeCampos(construirCamposItems(a))
    // Guarda contra el falso verde: sin chips, el for de abajo no compara nada.
    expect(chips.length).toBe(3)
    for (const chip of chips) {
      const antes = (a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length
      chip.quitar()
      expect((a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length, `el chip "${chip.etiqueta}" no reseteó la página`).toBe(antes + 1)
    }
  })

  it("Asignaciones: vale para TODOS los filtros con chip", () => {
    const a = argsAsig({ empresaFiltro: "e1", areaFiltro: "a1", empleadoFiltro: "p1" })
    const chips = chipsDeCampos(construirCamposAsignaciones(a))
    expect(chips.length).toBe(3)
    for (const chip of chips) {
      const antes = (a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length
      chip.quitar()
      expect((a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length, `el chip "${chip.etiqueta}" no reseteó la página`).toBe(antes + 1)
    }
  })

  it("🔴 los avanzados son DISTINTOS en cada pestaña, y ése es el criterio", () => {
    /*
     * Ítems: la pregunta diaria es del ESTADO ("¿qué hay disponible?"), y **Área** es el recorte a
     * otra entidad — un ítem no tiene área propia, se resuelve por quién lo tiene.
     * Asignaciones: la pregunta es "¿quién tiene qué?", el recorte estructural que más se usa es
     * el ÁREA, y **Colaborador** es el recorte a UNA persona.
     * ⚠️ Además, si Área también fuera avanzada en asignaciones, con una empresa elegida en el
     * sidebar la fila superior del panel quedaría SIN NINGÚN control a la vista.
     */
    expect(construirCamposItems(argsItems()).filter((c) => c.avanzado).map((c) => c.label)).toEqual(["Área"])
    expect(construirCamposAsignaciones(argsAsig()).filter((c) => c.avanzado).map((c) => c.label)).toEqual(["Colaborador"])
    // Y con empresa activa, asignaciones conserva Área a la vista.
    expect(construirCamposAsignaciones(argsAsig({ empresaActivaId: "e1" }))
      .filter((c) => !c.avanzado).map((c) => c.label)).toEqual(["Área"])
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

function tablaItems(props: Partial<Parameters<typeof ItemsInvTable>[0]> = {}) {
  return renderToStaticMarkup(
    <ItemsInvTable
      items={[]} loading={false} error={false} canWrite mostrarEmpresa deletingId={null}
      onReload={() => {}} onHistorial={() => {}} onEditar={() => {}} onEliminar={() => {}}
      chips={[chip("Estado", "Disponible")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

function tablaAsig(props: Partial<Parameters<typeof AsignacionesInvTable>[0]> = {}) {
  return renderToStaticMarkup(
    <AsignacionesInvTable
      asignaciones={[]} loading={false} error={false} canWrite mostrarEmpresa
      onReload={() => {}} onDevolver={() => {}}
      chips={[chip("Área", "Sistemas")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos mantiene el encabezado y usa los valores reales", () => {
  it("Ítems: las columnas siguen ahí y la frase nombra el filtro", () => {
    const html = tablaItems()
    for (const columna of ["Nombre", "Tipo", "N° Serie", "Estado", "Empresa", "Asignado a", "Alta"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
    expect(html).toContain('colSpan="8"')
    expect(html).toContain("No hay ítems con estado Disponible.")
  })

  it("Ítems: el esqueleto tiene la misma cantidad de columnas que la tabla", () => {
    const cargando = tablaItems({ loading: true })
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(8)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 8)
    expect(cargando).toContain("animate-shimmer")
  })

  it("Asignaciones: la frase nombra el filtro y el encabezado se queda", () => {
    const html = tablaAsig()
    expect(html).toContain("<thead")
    expect(html).toContain("No hay asignaciones activas con área Sistemas.")
  })

  it("🔴 Asignaciones SIN filtros lleva copy propio: la tabla sólo muestra lo VIGENTE", () => {
    /*
     * `textoVacio` diría "Todavía no hay asignaciones activas · Cuando se cargue la primera va a
     * aparecer acá", y eso confunde dos cosas: esta lista puede estar vacía con el inventario
     * entero asignado y devuelto a lo largo del año. No es "todavía no hay", es "hoy no hay nada
     * afuera" — que es una respuesta, no una carencia.
     */
    const html = tablaAsig({ chips: [] })
    expect(html).toContain("No hay ítems asignados en este momento")
    expect(html).toContain("sólo las asignaciones vigentes")
    expect(html).not.toContain("Cuando se cargue")
    expect(html).toContain("data-vacio")
  })
})

describe("🔴 el badge de estado de un ítem no es azul", () => {
  it("'Disponible' dejó de ser `bg-primary` y usa el par de éxito", () => {
    const html = tablaItems({
      chips: [], items: [{
        id: "i1", nombre: "Notebook", tipo: "Notebook", numero_serie: "X1",
        estado: "disponible", empresa_nombre: "Karstec", asignado_a: null, fecha_alta: "2026-01-05",
      } as Parameters<typeof ItemsInvTable>[0]["items"][number]],
    })
    expect(html).toContain("Disponible")
    expect(html).toContain("bg-success-wash")
    expect(html).not.toContain("bg-primary")
  })
})

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(d) el contador del pie sale de `total`, nunca de items.length", () => {
  it("las DOS pestañas le pasan `total={total}` y guardan el pie detrás de la carga", () => {
    for (const archivo of ["ItemsTab.tsx", "AsignacionesTab.tsx"]) {
      const src = readFileSync(path.resolve(__dirname, archivo), "utf8")
      const jsx = src.match(/<Pagination[\s\S]*?\/>/)
      expect(jsx, `${archivo} dejó de renderizar <Pagination>`).not.toBeNull()
      expect(jsx![0]).toContain("total={total}")
      expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0]), archivo).toBe(false)
      // Era `total > PAGE_SIZE` en las dos, sin guarda de carga.
      expect(sinComentarios(src), archivo).toContain("!loading && !error &&")
      expect(sinComentarios(src), archivo).not.toContain("total > PAGE_SIZE")
    }
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría las dos negaciones.
    expect(sinComentarios("if (total > PAGE_SIZE) {}")).toContain("total > PAGE_SIZE")
  })
})
