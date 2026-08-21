import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import { AVISO_CATALOGO_GLOBAL } from "./_avisoGlobal"
import { construirCampos } from "./_camposClientes"
import { ClientesTabla } from "./ClientesTabla"

/**
 * El patrón del bloque B sobre /clientes, que es **el catálogo GLOBAL de la tanda**: no pertenece
 * a ninguna empresa y el selector del sidebar no lo acota. Eso cambia dos cosas del patrón y las
 * dos se verifican acá: el vacío arranca IMPERSONAL (no hay empresa que sea sujeto) y la pantalla
 * lo DICE en el subtítulo en vez de dejar que alguien lo deduzca.
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos`, EL CABLEADO REAL. Con campos inventados el chip
 * llamaría a un `onChange` de mentira y el test pasaría con el cableado roto.
 *
 * ⚠️ (d) NO APLICA: `GET /api/clientes` no acepta `page` ni `page_size` — devuelve el catálogo
 * entero, así que no hay pie que armar. Está verificado abajo, en vez de simulado.
 */

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "clientes", "page.tsx")

describe("(a) el chip muestra el label legible, no el value crudo", () => {
  it("'Ver bajas' dice qué está mostrando, no el valor que viaja al backend", () => {
    const [chip] = chipsDeCampos(construirCampos({
      bajasFiltro: "todos", setBajasFiltro: vi.fn(), onFiltroChange: vi.fn(),
    }))
    expect(chip.etiqueta).toBe("Estado")
    expect(chip.valor).toBe("Activos y dados de baja")
  })

  it("🔴 el filtro PRODUCE CHIP — el botón que alternaba de antes no producía ninguno", () => {
    // Con el botón "Ver bajas"/"Ocultar bajas", la única señal de que la pantalla estaba
    // mostrando filas de más era el texto del propio botón: sin chip y sin contador.
    expect(chipsDeCampos(construirCampos({
      bajasFiltro: "todos", setBajasFiltro: vi.fn(), onFiltroChange: vi.fn(),
    }))).toHaveLength(1)
  })

  it("el default de la pantalla —sólo activos— NO produce chip", () => {
    // Es el default del backend (`incluir_inactivos=false`), así que "sin filtro puesto" y "lo
    // que el backend devuelve por omisión" significan lo mismo. Contracara del test de arriba:
    // sin esto, un `chipsDeCampos` que devolviera siempre un chip pasaría los dos.
    expect(chipsDeCampos(construirCampos({
      bajasFiltro: "", setBajasFiltro: vi.fn(), onFiltroChange: vi.fn(),
    }))).toEqual([])
  })

  it("no hay ningún filtro avanzado, y tampoco un filtro de empresa: el catálogo es global", () => {
    const campos = construirCampos({ bajasFiltro: "", setBajasFiltro: vi.fn(), onFiltroChange: vi.fn() })
    expect(campos.filter((c) => c.avanzado)).toEqual([])
    expect(campos.map((c) => c.label)).toEqual(["Estado"])
  })
})

describe("(b) quitar el chip quita ESE filtro y avisa a la pantalla", () => {
  it("llama a su setter con vacío y dispara onFiltroChange", () => {
    const a = { bajasFiltro: "todos", setBajasFiltro: vi.fn(), onFiltroChange: vi.fn() }
    chipsDeCampos(construirCampos(a))[0].quitar()
    expect(a.setBajasFiltro).toHaveBeenCalledWith("")
    // El listado no pagina, así que hoy `onFiltroChange` es un no-op en la página; el chip lo
    // llama igual para que el día que el backend acepte `page` no haya que rehacer el cableado.
    expect(a.onFiltroChange).toHaveBeenCalled()
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

function tabla(props: Partial<Parameters<typeof ClientesTabla>[0]> = {}) {
  return renderToStaticMarkup(
    <ClientesTabla
      clientes={[]} loading={false} error={null} canWrite
      onRetry={() => {}} onEdit={() => {}} onDelete={() => {}}
      chips={[chip("Estado", "Activos y dados de baja")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos mantiene el encabezado y usa los valores reales", () => {
  it("las columnas siguen ahí y el vacío es una fila de la tabla", () => {
    const html = tabla()
    expect(html).toContain("Cliente")
    expect(html).toContain("Estado")
    expect(html).toContain("<thead")
    expect(html).toContain('colSpan="3"')
  })

  it("🔴 la frase arranca IMPERSONAL: este catálogo no pertenece a ninguna empresa", () => {
    // El sujeto del texto vacío es siempre la EMPRESA ("Karstec no tiene…"), y acá no hay
    // ninguna: el catálogo es del grupo desde las migraciones 108/109.
    const html = tabla()
    expect(html).toContain("No hay clientes con estado Activos y dados de baja.")
    expect(html).not.toContain("no tiene clientes")
  })

  it("sin filtros no ofrece quitar nada: ofrece crear el primero", () => {
    const html = tabla({ chips: [], accionVacio: <button>Crear el primero</button> })
    expect(html).toContain("Todavía no hay clientes")
    expect(html).toContain("Crear el primero")
    expect(html).not.toContain("Limpiar todo")
  })

  it("el esqueleto tiene la misma cantidad de columnas que la tabla, con y sin permiso", () => {
    const cargando = tabla({ loading: true })
    expect(cargando).toContain("<thead")
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(3)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 3)
    expect(cargando).toContain("animate-shimmer")
    const sinPermiso = tabla({ loading: true, canWrite: false })
    expect((sinPermiso.match(/<th[ >]/g) ?? []).length).toBe(2)
    expect((sinPermiso.match(/<td[ >]/g) ?? []).length).toBe(8 * 2)
  })
})

describe("🔴 el badge de estado no es azul", () => {
  it("'Activo' dejó de ser `bg-primary` y usa el par de éxito", () => {
    const html = tabla({
      chips: [], clientes: [{
        id: "c1", nombre: "Acme", activo: true, created_at: "2026-08-01T00:00:00Z", updated_at: null,
      }],
    })
    expect(html).toContain("Activo")
    expect(html).toContain("bg-success-wash")
    expect(html).not.toContain("bg-primary")
  })
})

describe("🔴 la pantalla DICE que es un catálogo global", () => {
  it("el aviso está en el subtítulo del encabezado, no escondido en un tooltip", () => {
    /*
     * Es lo contrario a lo que hace el resto del producto: quien está acostumbrado a que el
     * sidebar filtre va a suponer que ve "los clientes de esta empresa", y va a crear un
     * duplicado que el índice único global rechaza con un 409. Se verifica que el texto viaje al
     * `description` del PageHeader y no a cualquier otro lado.
     */
    const pagina = readFileSync(PAGINA, "utf8")
    expect(pagina).toContain("AVISO_CATALOGO_GLOBAL")
    // 🔑 La ventana es `[\s\S]{0,300}?` y NO `[^}]*`: el subtítulo es un template literal con
    // `${clientes.length}` adentro, así que la primera `}` aparece MUCHO antes del aviso y una
    // clase negada lo perdía. El test rojeaba con el código correcto.
    expect(pagina).toMatch(/description=\{[\s\S]{0,300}?AVISO_CATALOGO_GLOBAL/)
    // Y el texto dice las dos cosas que hay que saber: que el sidebar no filtra y que el nombre
    // es único en el sistema entero.
    expect(AVISO_CATALOGO_GLOBAL).toContain("sidebar no lo filtra")
    expect(AVISO_CATALOGO_GLOBAL).toContain("único en el sistema entero")
  })

  it("(d) NO APLICA: la pantalla no pagina, y por eso no monta <Pagination>", () => {
    // `GET /api/clientes` no acepta `page` ni `page_size`. Un pie tendría que derivarse del
    // array ya traído, que es el bug que `paginacionTotales.test.ts` persigue.
    const pagina = readFileSync(PAGINA, "utf8")
    expect(pagina).not.toContain("<Pagination")
    // Contracara: el archivo que se está leyendo es el que se cree. Sin esto, un path mal armado
    // devolvería texto vacío y la aserción de arriba pasaría sin mirar nada.
    expect(pagina).toContain("<ClientesTabla")
  })
})
