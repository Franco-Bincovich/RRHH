import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { EquipoTable } from "./EquipoTable"

/**
 * El patrón del bloque B sobre /equipo, que es **el caso distinto de la tanda**: no tiene filtros
 * ni paginación, así que (a), (b) y (d) NO APLICAN y este archivo lo dice en vez de simularlos.
 * `GET /api/equipo` no acepta un solo Query y devuelve la lista entera; sin filtros no hay chips
 * y sin `total` no hay pie.
 *
 * Lo que sí se verifica es (c) —la tabla conserva su encabezado en los tres estados— y las dos
 * decisiones propias de esta pantalla: el texto del vacío es PROPIO (no el de `textoVacio`, que
 * acá sería falso) y no hay columna de acciones.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · que el vacío volviera a reemplazar la tabla entera: desaparece `<thead>`.
 *   · que alguien "unificara" el copy usando `TablaVacia`: la pantalla pasaría a decirle a un
 *     jefe sin reportes que "cuando se cargue el primero va a aparecer acá", cosa que él no puede
 *     hacer.
 *   · que el esqueleto declarara sus propias columnas: se desalinean al llegar los datos.
 */

const MIEMBROS = [
  { id: "1", nombre: "Ana", apellido: "Pérez", empresa: "Karstec" },
  { id: "2", nombre: "Luis", apellido: "Gómez", empresa: null },
] as Parameters<typeof EquipoTable>[0]["items"]

function tabla(props: Partial<Parameters<typeof EquipoTable>[0]> = {}) {
  return renderToStaticMarkup(
    <EquipoTable items={[]} loading={false} error={false} onRetry={() => {}} {...props} />,
  )
}

describe("(c) el encabezado sigue puesto en los tres estados", () => {
  it("con datos", () => {
    const html = tabla({ items: MIEMBROS })
    expect(html).toContain("<thead")
    for (const columna of ["Apellido", "Nombre", "Empresa"]) {
      expect(html, `desapareció la columna ${columna}`).toContain(columna)
    }
    // La empresa vacía sale como guion, no en blanco: acá el ownership puede cruzar sociedades.
    expect(html).toContain("—")
  })

  it("vacío: el bloque es una fila de la tabla, no un panel que la reemplaza", () => {
    const html = tabla()
    expect(html).toContain("<thead")
    expect(html).toContain("<table")
    expect(html).toContain('colSpan="3"')
    // Y queda fuera del hover de datos: no es un registro que se pueda abrir.
    expect(html).toContain("data-vacio")
  })

  it("cargando: el esqueleto tiene la MISMA cantidad de columnas que la tabla", () => {
    const cargando = tabla({ loading: true })
    expect(cargando).toContain("<thead")
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(3)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 3)
    expect(cargando).toContain("animate-shimmer")
  })
})

describe("🔴 el texto del vacío es PROPIO, no el genérico de textoVacio()", () => {
  it("dice que no te asignaron gente, no que falte cargar el primer registro", () => {
    const html = tabla()
    expect(html).toContain("Todavía no tenés colaboradores a cargo")
    expect(html).toContain("Cuando Capital Humano te asigne personas")
    // La frase genérica sería falsa acá: el que mira no puede cargar a nadie.
    expect(html).not.toContain("Cuando se cargue el primero")
  })
})

describe("(a) (b) (d) NO APLICAN: la pantalla no filtra ni pagina", () => {
  it("la página no monta <FiltersBar> ni <Pagination>, y eso es lo correcto", () => {
    /*
     * Ponerle chips a una pantalla que no filtra sería inventar filtros que el backend no acepta,
     * y un pie sin `total` del backend tendría que derivarse del array — el bug que
     * `paginacionTotales.test.ts` persigue. Si algún día `GET /api/equipo` acepta Query, ESTE test
     * es el que hay que dar vuelta.
     */
    const pagina = readFileSync(
      path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "equipo", "page.tsx"), "utf8",
    )
    expect(pagina).not.toContain("<FiltersBar")
    expect(pagina).not.toContain("<Pagination")
    // Contracara: el archivo que se está leyendo es el que se cree. Sin esto, un path mal armado
    // devolvería un texto vacío y las dos aserciones de arriba pasarían sin mirar nada.
    expect(pagina).toContain("<EquipoTable")
  })
})
