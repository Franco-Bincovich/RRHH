import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import { construirCampos } from "./_camposAreas"
import { AreasTabla } from "./AreasTabla"

/**
 * Los cuatro puntos del patrón del bloque B sobre /areas: (a) el chip dice el label legible,
 * (b) quitarlo quita ESE filtro y resetea la página, (c) el vacío conserva el encabezado y habla
 * con los valores reales, (d) el pie sale de `total`.
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos`, EL CABLEADO REAL DE LA PANTALLA, no contra campos
 * inventados. Con campos de mentira el chip llamaría a un `onChange` de mentira y el test pasaría
 * con el cableado roto — el falso verde que CLAUDE.md documenta.
 *
 * ⚠️ (b) TIENE UNA VUELTA PROPIA DE ESTA PANTALLA: acá no hay `onFiltroChange`. El reset a la
 * página 1 vive DENTRO de `setSearch`, en `useAreas` (`const setSearch = (v) => { setPage(1);
 * setSearchRaw(v) }`), así que el chip lo hereda por llamar al MISMO setter que el control. Se
 * verifica en dos mitades: que el chip llame a `setSearch("")` y que ese setter resetee.
 */

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "areas", "page.tsx")
const HOOK = path.resolve(__dirname, "useAreas.ts")

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca y
 *  la función devolvería el código intacto — verde en la Mac, rojo en la Lenovo. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(a) el chip muestra el label legible, no el value crudo", () => {
  it("el buscador se llama 'Nombre', así que la frase del vacío se lee en español", () => {
    // Con la etiqueta "Buscar" —la que usa /empleados— el vacío diría "No hay áreas con buscar
    // Sistemas". Acá el buscador es el ÚNICO filtro, así que esa etiqueta ES la frase entera.
    const [chip] = chipsDeCampos(construirCampos({ search: "Sistemas", setSearch: vi.fn() }))
    expect(chip.etiqueta).toBe("Nombre")
    expect(chip.valor).toBe("Sistemas")
  })

  it("un buscador con sólo espacios no produce chip: no se podría quitar", () => {
    expect(chipsDeCampos(construirCampos({ search: "   ", setSearch: vi.fn() }))).toEqual([])
  })

  it("no hay ningún filtro avanzado: con uno solo, esconderlo deja la pantalla sin controles", () => {
    expect(construirCampos({ search: "", setSearch: vi.fn() }).filter((c) => c.avanzado)).toEqual([])
  })
})

describe("(b) quitar el chip llama al MISMO setter del control, y ese setter resetea la página", () => {
  it("el chip llama a setSearch con vacío", () => {
    const setSearch = vi.fn()
    chipsDeCampos(construirCampos({ search: "Sistemas", setSearch }))[0].quitar()
    expect(setSearch).toHaveBeenCalledWith("")
  })

  it("y `setSearch` de useAreas vuelve a la página 1 antes de mover el texto", () => {
    /*
     * La otra mitad. Se lee del hook porque el reset NO es un `onFiltroChange` que se pueda
     * espiar: está adentro del setter, y vitest corre sin jsdom (no se puede montar el hook).
     * Sin esta mitad, el test de arriba pasaría con el reset borrado y el usuario quedaría en la
     * página 3 de un listado que ahora tiene una — la tabla vacía sobre un término que sí tiene
     * áreas, indistinguible de "no encontré nada".
     */
    const codigo = sinComentarios(readFileSync(HOOK, "utf8"))
    expect(codigo).toContain("const setSearch = (v: string) => { setPage(1); setSearchRaw(v) }")
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría la aserción de arriba.
    expect(sinComentarios("const setSearch = 1")).toContain("const setSearch")
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

function tabla(props: Partial<Parameters<typeof AreasTabla>[0]> = {}) {
  return renderToStaticMarkup(
    <AreasTabla
      areas={[]} loading={false} error={false} canWrite
      onRetry={() => {}} onEdit={() => {}} onDelete={() => {}}
      chips={[chip("Nombre", "Sistemas")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos mantiene el encabezado y usa los valores reales", () => {
  it("las columnas siguen ahí y el vacío es una fila de la tabla", () => {
    const html = tabla()
    for (const columna of ["Nombre", "Descripción", "Responsable", "Colaboradores"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
    expect(html).toContain('colSpan="5"')
  })

  it("la frase arranca IMPERSONAL: en esta pantalla la empresa no es un chip", () => {
    // La empresa de /areas la manda el selector del sidebar (viaja como query param, es el único
    // módulo así). Sin chip de empresa no hay sujeto, y la frase empieza por "No hay…".
    expect(tabla()).toContain("No hay áreas con nombre Sistemas.")
  })

  it("sin filtros no ofrece quitar nada: ofrece crear la primera", () => {
    const html = tabla({ chips: [], accionVacio: <button>Crear la primera</button> })
    expect(html).toContain("Todavía no hay áreas")
    expect(html).toContain("Crear la primera")
    expect(html).not.toContain("Limpiar todo")
  })

  it("el esqueleto tiene la misma cantidad de columnas que la tabla, con y sin permiso", () => {
    const cargando = tabla({ loading: true })
    expect(cargando).toContain("<thead")
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(5)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 5)
    expect(cargando).toContain("animate-shimmer")
    // Sin permiso de escritura la columna de acciones no existe, ni en el encabezado ni en el
    // esqueleto: una columna vacía con su título es una promesa que la pantalla no cumple.
    const sinPermiso = tabla({ loading: true, canWrite: false })
    expect((sinPermiso.match(/<th[ >]/g) ?? []).length).toBe(4)
    expect((sinPermiso.match(/<td[ >]/g) ?? []).length).toBe(8 * 4)
  })
})

describe("(d) el contador del pie sale de `total`, nunca de areas.length", () => {
  it("la página le pasa `total={total}` a <Pagination>", () => {
    const jsx = readFileSync(PAGINA, "utf8").match(/<Pagination[\s\S]*?\/>/)
    expect(jsx, "la página dejó de renderizar <Pagination>").not.toBeNull()
    expect(jsx![0]).toContain("total={total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0])).toBe(false)
  })

  it("🔴 el pie va SIEMPRE que haya filas, y sólo después de cargar", () => {
    /*
     * Era `total > PAGE_SIZE`. Y la guarda `!loading` es NUEVA y necesaria: hasta esta tanda la
     * página hacía un `return` temprano durante la carga que se llevaba la pantalla entera, así
     * que el pie no podía dibujarse sobre el esqueleto por accidente. Al mover los estados
     * adentro de la tabla esa protección desaparece — sin la guarda, la barra mostraría el total
     * del pedido ANTERIOR mientras carga el nuevo.
     *
     * 🔑 Se mira el código SIN COMENTARIOS: la explicación de por qué se sacó la condición vieja
     * la CONTIENE, y un barrido por texto plano marcaría al archivo ya arreglado.
     */
    const codigo = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(codigo).toContain("!loading && !error && areas.length > 0 && (")
    expect(codigo).not.toContain("total > PAGE_SIZE")
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría las dos de arriba.
    expect(sinComentarios("if (total > PAGE_SIZE) {}")).toContain("total > PAGE_SIZE")
  })
})
