import { readdirSync, readFileSync } from "node:fs"
import { join, resolve, sep } from "node:path"

import { describe, expect, it } from "vitest"

import { construirCampos } from "@/components/features/empleados/_camposEmpleados"
import { chipsDeCampos } from "@/components/ui/filtrosChips"

/**
 * 🔴 BARRIDO ESTRUCTURAL — **"Limpiar todo" restituye: ningún filtro puede quedar puesto sin chip.**
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * EL BUG, Y POR QUÉ NO SE VE
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * Reportado el 24/8/2026 en /empleados: **20 filas al entrar, 16 después de limpiar los filtros**,
 * en desktop y en mobile. La pantalla queda diciendo "0 filtros activos" sobre un listado
 * recortado, así que no hay nada que mirar para entender por qué faltan filas.
 *
 * LA CAUSA es la composición de dos cosas correctas por separado:
 *   1. "Limpiar todo" es **cada chip quitándose a sí mismo** (`FiltrosActivos`), y eso es a
 *      propósito: así hereda gratis el reseteo a página 1 y los efectos propios de cada filtro
 *      (el de Empresa además limpia Área). No se toca.
 *   2. Los campos cuyo catálogo llega por fetch se renderizaban **sólo si el catálogo tenía
 *      opciones** (`...(a.areas.length > 0 ? [{…}] : [])`).
 * Juntas: si el catálogo queda vacío —el fetch falló y cae en su `.catch(() => setAreas([]))`, o
 * se cambió a una empresa que no tiene áreas ni proyectos— el campo **desaparece de `campos`**,
 * `chipsDeCampos` no produce chip, y el forEach no tiene nada que quitar. El valor sigue vivo en
 * el `useState` del hook y **sigue viajando al backend en cada pedido**.
 *
 * EL FIX es de una línea por campo y ya estaba escrito como intención en `filtrosChips.ts`:
 * *"un filtro activo INVISIBLE es la pantalla mostrando 4 filas de 31 sin decir por qué"*. Ese
 * archivo resuelve el caso del valor que no está en `opciones` (muestra el valor crudo) pero no
 * podía hacer nada con el campo ausente. Ahora el campo se renderiza si **hay opciones O hay
 * valor**. Medido: **31 campos en 11 módulos** estaban así.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *   · El primer bloque ejercita `construirCampos` REAL con el catálogo vacío y el filtro puesto,
 *     que es exactamente el estado que producía el bug. Con el catálogo lleno —que es como se
 *     testearía "naturalmente"— el bug no existe y el test pasaría con el código roto.
 *   · El segundo barre el árbol y no una lista escrita a mano, así que el campo condicionado
 *     número 32 entra solo.
 */

// ═════════════════════════════════════════════════════════════════════════════
// 1) El caso concreto que se reportó, sobre la pantalla que lo reportó
// ═════════════════════════════════════════════════════════════════════════════

/** Argumentos de `construirCampos` con todo en cero: el estado inicial de /empleados. */
const VACIO = {
  search: "", setSearch: () => {},
  empresaActivaId: null, empresas: [], empresaFiltro: "", setEmpresaFiltro: () => {},
  areas: [], areaFiltro: "", setAreaFiltro: () => {},
  estadoFiltro: "", setEstadoFiltro: () => {},
  liderFiltro: "", setLiderFiltro: () => {},
  sinManagerFiltro: "", setSinManagerFiltro: () => {},
  proyectos: [], proyectoFiltro: "", setProyectoFiltro: () => {},
  onFiltroChange: () => {},
}

describe("🔴 Un filtro con valor SIEMPRE tiene su chip, aunque su catálogo esté vacío", () => {
  it("el Área filtra aunque `areas` haya quedado vacío — y se puede quitar", () => {
    // El estado exacto del bug: el usuario eligió un área, después el catálogo se vació (fetch
    // fallido, o cambio a una empresa sin áreas) y el filtro siguió recortando el listado.
    const campos = construirCampos({ ...VACIO, areas: [], areaFiltro: "area-1" })
    const chips = chipsDeCampos(campos)
    const area = chips.find((c) => c.clave === "Área")
    expect(area, "el filtro de Área está puesto y NO produce chip: 'Limpiar todo' no lo alcanza")
      .toBeDefined()
    // Muestra el valor crudo, que es feo por un instante y es lo decidido en `filtrosChips`:
    // un filtro activo invisible es peor que uno con el id a la vista.
    expect(area!.valor).toBe("area-1")
  })

  it("lo mismo para Proyecto y Empresa, que son los otros dos catálogos por fetch", () => {
    const conProyecto = chipsDeCampos(construirCampos({ ...VACIO, proyectoFiltro: "proy-1" }))
    expect(conProyecto.map((c) => c.clave)).toContain("Proyecto")

    const conEmpresa = chipsDeCampos(construirCampos({ ...VACIO, empresaFiltro: "emp-1" }))
    expect(conEmpresa.map((c) => c.clave)).toContain("Empresa")
  })

  it("sin valor y sin catálogo, el campo NO aparece (no se ensucia la barra)", () => {
    // La contracara. Sin esto, "renderizar siempre" también pasaría el test de arriba y la barra
    // de /empleados mostraría tres selectores vacíos e inútiles en la carga inicial.
    const campos = construirCampos(VACIO)
    const labels = campos.map((c) => c.label)
    expect(labels).not.toContain("Área")
    expect(labels).not.toContain("Proyecto")
    expect(labels).not.toContain("Empresa")
  })

  it("«Limpiar todo» sobre TODOS los filtros puestos los quita a todos", () => {
    // El gesto completo: se registran los `quitar()` y se verifica que ninguno quede afuera.
    const quitados: string[] = []
    const campos = construirCampos({
      ...VACIO,
      areas: [], areaFiltro: "area-1", setAreaFiltro: () => quitados.push("area"),
      proyectos: [], proyectoFiltro: "proy-1", setProyectoFiltro: () => quitados.push("proyecto"),
      empresaFiltro: "emp-1", setEmpresaFiltro: () => quitados.push("empresa"),
      estadoFiltro: "activo", setEstadoFiltro: () => quitados.push("estado"),
      sinManagerFiltro: "si", setSinManagerFiltro: () => quitados.push("sin_manager"),
      search: "juan", setSearch: () => quitados.push("search"),
    })
    const chips = chipsDeCampos(campos)
    chips.forEach((c) => c.quitar())
    for (const esperado of ["area", "proyecto", "empresa", "estado", "sin_manager", "search"]) {
      expect(quitados, `«Limpiar todo» no quitó ${esperado}`).toContain(esperado)
    }
  })
})

// ═════════════════════════════════════════════════════════════════════════════
// 2) El barrido: que no vuelva a aparecer un campo condicionado sólo al catálogo
// ═════════════════════════════════════════════════════════════════════════════

const RAIZ = resolve(__dirname, "..", "..")

function archivosDe(carpeta: string): string[] {
  const salida: string[] = []
  const recorrer = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (e.name === "node_modules" || e.name.startsWith(".")) continue
      const p = join(dir, e.name)
      if (e.isDirectory()) recorrer(p)
      else if (/\.tsx?$/.test(e.name) && !/\.test\./.test(e.name)) {
        // Normalizado a "/" donde nacen los paths — en Windows `join` usa "\" y comparar un
        // tramo con "/" literal descubre CERO archivos y pasa en verde.
        salida.push(p.slice(RAIZ.length + 1).split(sep).join("/"))
      }
    }
  }
  recorrer(join(RAIZ, carpeta))
  return salida
}

const ARCHIVOS = [...archivosDe("components"), ...archivosDe("app")]

/**
 * `...( COND ? [{ tipo: "…" as const, label: "…", value: VALOR` — un campo de filtro que se
 * renderiza condicionalmente. Es la forma exacta que usan los once módulos.
 */
const CAMPO_CONDICIONADO =
  /\.\.\.\(([^?]+?)\s*\?\s*\[\{\s*tipo:\s*"[a-z]+" as const,\s*label:\s*"[^"]*",\s*value:\s*([A-Za-z0-9_.]+)/g

interface Hallazgo { archivo: string; cond: string; valor: string }

const CONDICIONADOS: Hallazgo[] = []
for (const archivo of ARCHIVOS) {
  const src = readFileSync(join(RAIZ, archivo), "utf-8")
  for (const m of src.matchAll(CAMPO_CONDICIONADO)) {
    CONDICIONADOS.push({ archivo, cond: m[1].trim(), valor: m[2] })
  }
}

/** El campo depende de un catálogo que puede quedar vacío. */
const dependeDeCatalogo = (h: Hallazgo) => h.cond.includes(".length > 0")
/** …y la condición NO contempla el valor del filtro. */
const ignoraElValor = (h: Hallazgo) => !h.cond.includes(h.valor)

describe("Barrido: ningún campo de filtro se condiciona sólo a que su catálogo tenga opciones", () => {
  it("el barrido encuentra campos condicionados (si no, no está mirando nada)", () => {
    // Guarda contra el falso verde: si el patrón dejara de matchear —porque el estilo del repo
    // cambió— CONDICIONADOS quedaría vacío y "no hay infractores" pasaría sin haber mirado uno.
    expect(CONDICIONADOS.length).toBeGreaterThanOrEqual(25)
    expect(ARCHIVOS.length).toBeGreaterThanOrEqual(300)
  })

  it("todos los que dependen de un catálogo contemplan además su propio valor", () => {
    const infractores = CONDICIONADOS.filter((h) => dependeDeCatalogo(h) && ignoraElValor(h))
      .map((h) => `${h.archivo}: ${h.cond}  (valor: ${h.valor})`)
    expect(infractores, "un filtro con valor y catálogo vacío queda SIN CHIP: «Limpiar todo» "
      + "no lo alcanza y el listado sigue recortado sin decir por qué. "
      + "La condición tiene que ser `(catalogo.length > 0) || valor`.").toEqual([])
  })

  it("el detector reconoce la forma rota (si no, el barrido no prueba nada)", () => {
    // Sin esto, un regex que dejara de matchear la forma peligrosa daría verde para siempre.
    const roto: Hallazgo = { archivo: "x", cond: "a.areas.length > 0", valor: "a.areaFiltro" }
    const sano: Hallazgo = { archivo: "x", cond: "(a.areas.length > 0) || a.areaFiltro", valor: "a.areaFiltro" }
    expect(dependeDeCatalogo(roto) && ignoraElValor(roto)).toBe(true)
    expect(dependeDeCatalogo(sano) && ignoraElValor(sano)).toBe(false)
  })
})
