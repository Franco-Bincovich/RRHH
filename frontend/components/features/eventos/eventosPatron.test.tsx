import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import { construirCampos } from "./_camposEventos"
import { EventosTabla } from "./EventosTabla"

/**
 * Los cuatro puntos del patrón del bloque B sobre /eventos.
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos`, EL CABLEADO REAL. Con campos inventados el chip
 * llamaría a un `onChange` de mentira y el test pasaría con el cableado roto.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (a) que "ver resueltos" volviera a ser un botón que alterna: no produce chip, y la agenda
 *     muestra filas de más sin ninguna señal en el panel.
 *   · (b) que el setter dejara de resetear la página.
 *   · (c) que el vacío volviera a reemplazar la tabla entera: desaparece `<thead>`.
 *   · (d) que la página le pasara `eventos.length` a `<Pagination>`, o que sacara la guarda de
 *     `!loading` y volviera a dibujar el pie sobre el esqueleto.
 */

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "eventos", "page.tsx")
const HOOK = path.resolve(__dirname, "useEventos.ts")

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(a) el chip muestra el label legible, no el value crudo", () => {
  it("dice qué está mostrando, no el valor que viaja al backend", () => {
    const [chip] = chipsDeCampos(construirCampos({
      resueltosFiltro: "todos", setResueltosFiltro: vi.fn(), onFiltroChange: vi.fn(),
    }))
    expect(chip.etiqueta).toBe("Estado")
    expect(chip.valor).toBe("Pendientes y resueltos")
  })

  it("🔴 el filtro PRODUCE CHIP — el botón que alternaba de antes no producía ninguno", () => {
    expect(chipsDeCampos(construirCampos({
      resueltosFiltro: "todos", setResueltosFiltro: vi.fn(), onFiltroChange: vi.fn(),
    }))).toHaveLength(1)
  })

  it("el default —sólo pendientes— NO produce chip: es el default del backend", () => {
    // Contracara: sin esto, un `chipsDeCampos` que devolviera siempre un chip pasaría los dos.
    expect(chipsDeCampos(construirCampos({
      resueltosFiltro: "", setResueltosFiltro: vi.fn(), onFiltroChange: vi.fn(),
    }))).toEqual([])
  })

  it("no hay ningún filtro avanzado: con uno solo, esconderlo deja la pantalla sin controles", () => {
    expect(construirCampos({
      resueltosFiltro: "", setResueltosFiltro: vi.fn(), onFiltroChange: vi.fn(),
    }).filter((c) => c.avanzado)).toEqual([])
  })
})

describe("(b) quitar el chip llama al MISMO setter del control, y ese setter resetea la página", () => {
  it("el chip llama al setter con vacío", () => {
    const setResueltosFiltro = vi.fn()
    chipsDeCampos(construirCampos({
      resueltosFiltro: "todos", setResueltosFiltro, onFiltroChange: vi.fn(),
    }))[0].quitar()
    expect(setResueltosFiltro).toHaveBeenCalledWith("")
  })

  it("y el setter que la página le pasa vuelve a la página 1", () => {
    /*
     * La otra mitad, y acá el reset NO es un `onFiltroChange` que se pueda espiar: vive DENTRO
     * del setter que expone `useEventos`. Se lee del hook porque vitest corre sin jsdom y no se
     * puede montar. Sin esta mitad, el test de arriba pasaría con el reset borrado y el usuario
     * quedaría en la página 4 de un listado que ahora tiene una.
     */
    const codigo = sinComentarios(readFileSync(HOOK, "utf8"))
    expect(codigo).toContain("setResueltosFiltro: (v: string) => { setResueltosFiltro(v); setPage(1) }")
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría la aserción de arriba.
    expect(sinComentarios("const a = 1")).toContain("const a = 1")
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

const EVENTO = {
  id: "e1", empresa_id: "emp1", nombre: "Feriado puente", fecha: "2026-12-08",
  descripcion: null, dias_aviso: 7, es_publica: true,
  resuelta: false, resuelta_at: null, resuelta_por: null, resuelta_por_nombre: null,
  created_by: "u1", created_by_nombre: "Ana", empresa_nombre: "Karstec",
  created_at: "2026-01-01T00:00:00Z", updated_at: null,
} as Parameters<typeof EventosTabla>[0]["eventos"][number]

function tabla(props: Partial<Parameters<typeof EventosTabla>[0]> = {}) {
  return renderToStaticMarkup(
    <EventosTabla
      eventos={[]} loading={false} error={null} canWrite
      onRetry={() => {}} onEdit={() => {}} onDelete={() => {}} onResuelta={() => {}}
      chips={[chip("Estado", "Pendientes y resueltos")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos mantiene el encabezado y usa los valores reales", () => {
  it("las columnas siguen ahí y el vacío es una fila de la tabla", () => {
    const html = tabla()
    for (const columna of ["Recordatorio", "Fecha", "Aviso", "Visibilidad", "Estado"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
    expect(html).toContain('colSpan="6"')
  })

  it("la frase arranca impersonal y nombra el filtro puesto", () => {
    expect(tabla()).toContain("No hay recordatorios con estado Pendientes y resueltos.")
  })

  it("sin filtros ofrece crear el primero", () => {
    const html = tabla({ chips: [], accionVacio: <button>Crear el primero</button> })
    expect(html).toContain("Todavía no hay recordatorios")
    expect(html).toContain("Crear el primero")
    expect(html).not.toContain("Limpiar todo")
  })

  it("el esqueleto tiene la misma cantidad de columnas que la tabla, con y sin permiso", () => {
    const cargando = tabla({ loading: true })
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(6)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 6)
    expect(cargando).toContain("animate-shimmer")
    const sinPermiso = tabla({ loading: true, canWrite: false })
    expect((sinPermiso.match(/<th[ >]/g) ?? []).length).toBe(5)
  })
})

describe("🔴 el badge de visibilidad no es azul", () => {
  it("'Del equipo' dejó de ser `bg-primary`", () => {
    const html = tabla({ chips: [], eventos: [EVENTO] })
    expect(html).toContain("Del equipo")
    expect(html).not.toContain("bg-primary")
  })
})

describe("(d) el contador del pie sale de `total`, nunca de eventos.length", () => {
  it("la página le pasa `total={agenda.total}` a <Pagination>", () => {
    const jsx = readFileSync(PAGINA, "utf8").match(/<Pagination[\s\S]*?\/>/)
    expect(jsx, "la página dejó de renderizar <Pagination>").not.toBeNull()
    expect(jsx![0]).toContain("total={agenda.total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0])).toBe(false)
  })

  it("🔴 el pie va SIEMPRE que haya filas, y NUNCA sobre el esqueleto", () => {
    // Antes la barra colgaba del bloque `eventos.length > 0`, protegido por los `return`
    // tempranos de carga y error; al mover los estados a la tabla, la guarda pasa a ser explícita.
    const codigo = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(codigo).toContain("!agenda.loading && !agenda.error && agenda.eventos.length > 0 && (")
  })
})
