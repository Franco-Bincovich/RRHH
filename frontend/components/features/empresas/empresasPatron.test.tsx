import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { AVISO_CATALOGO_GLOBAL } from "./_avisoGlobal"
import { EmpresasTable } from "./EmpresasTable"

/**
 * El patrón del bloque B sobre /empresas, que junto con /usuarios es **el otro caso sin filtros**
 * de la tanda: `GET /api/empresas` no acepta un solo Query y devuelve la lista entera. Por eso
 * (a), (b) y (d) NO APLICAN, y este archivo lo dice en vez de simularlos — ponerle chips a una
 * pantalla que no filtra sería inventar filtros que el backend no puede honrar, y un pie tendría
 * que derivarse del array ya traído.
 *
 * Lo que sí se verifica es (c) —la tabla conserva su encabezado en los tres estados—, que el
 * badge de estado dejó de ser azul, que la pantalla DICE que el sidebar no la acota, y que el
 * chevron al detalle no manda a nadie a una ruta prohibida.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · que el vacío volviera a reemplazar la tabla entera: desaparece `<thead>`.
 *   · que el esqueleto declarara sus propias columnas: se desalinean al llegar los datos.
 *   · que "Activa" volviera a `variant="default"`: reaparece `bg-primary` en una celda de datos.
 */

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "empresas", "page.tsx")

const EMPRESAS = [
  { id: "e1", nombre: "Karstec", cuit: "30-12345678-9", email: "a@b.com", activa: true },
  { id: "e2", nombre: "Dosuba", cuit: null, email: null, activa: false },
] as Parameters<typeof EmpresasTable>[0]["empresas"]

function tabla(props: Partial<Parameters<typeof EmpresasTable>[0]> = {}) {
  return renderToStaticMarkup(
    <EmpresasTable
      empresas={[]} loading={false} error={false} canWrite
      onRetry={() => {}} onEdit={() => {}} onToggle={() => {}} togglingId={null}
      {...props}
    />,
  )
}

describe("(c) el encabezado sigue puesto en los tres estados", () => {
  it("con datos, y los vacíos salen como guion en vez de en blanco", () => {
    const html = tabla({ empresas: EMPRESAS })
    expect(html).toContain("<thead")
    for (const columna of ["Nombre", "CUIT", "Email", "Estado"]) {
      expect(html, `desapareció la columna ${columna}`).toContain(columna)
    }
    // Una celda en blanco no distingue "sin dato" de "no cargó".
    expect(html).toContain("—")
  })

  it("vacío: el bloque es una fila de la tabla, no un panel que la reemplaza", () => {
    const html = tabla({ accionVacio: <button>Nueva empresa</button> })
    expect(html).toContain("<thead")
    expect(html).toContain("<table")
    expect(html).toContain('colSpan="5"')
    expect(html).toContain("Todavía no hay empresas")
    expect(html).toContain("Nueva empresa")
    // Sin filtros no hay nada que limpiar, así que la salida "Limpiar todo" no aparece nunca.
    expect(html).not.toContain("Limpiar todo")
  })

  it("cargando: el esqueleto tiene la MISMA cantidad de columnas que la tabla", () => {
    const cargando = tabla({ loading: true })
    expect(cargando).toContain("<thead")
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(5)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 5)
    expect(cargando).toContain("animate-shimmer")
  })

  it("la columna de acciones va SIEMPRE, incluso sin permiso de escritura", () => {
    // Ahí queda el chevron al detalle, que es una LECTURA. Editar y el toggle sí desaparecen.
    const sinPermiso = tabla({ empresas: EMPRESAS, canWrite: false })
    expect(sinPermiso).toContain("Ver la ficha de Karstec")
    expect(sinPermiso).not.toContain("Editar Karstec")
    expect(sinPermiso).not.toContain("Desactivar Karstec")
    // Contracara: con permiso están las tres.
    const conPermiso = tabla({ empresas: EMPRESAS, canWrite: true })
    expect(conPermiso).toContain("Editar Karstec")
    expect(conPermiso).toContain("Desactivar Karstec")
  })

  it("🔴 el chevron apunta al detalle de la empresa, que el rol de esta pantalla SÍ puede abrir", () => {
    // La regla: antes de poner un chevron hay que verificar que el destino no lo rebote el
    // AuthGuard. `/empresas/[id]` cae en la sección EMPRESA, la misma que gatea este listado.
    expect(tabla({ empresas: EMPRESAS })).toContain('href="/empresas/e1"')
  })
})

describe("🔴 el badge de estado no es azul", () => {
  it("'Activa' usa el par de éxito y 'Inactiva' el neutro", () => {
    const html = tabla({ empresas: EMPRESAS })
    expect(html).toContain("Activa")
    expect(html).toContain("Inactiva")
    expect(html).toContain("bg-success-wash")
    expect(html).not.toContain("bg-primary")
  })
})

describe("🔴 la pantalla DICE que el sidebar no la acota", () => {
  it("el aviso viaja al subtítulo del encabezado", () => {
    const pagina = readFileSync(PAGINA, "utf8")
    expect(pagina).toContain("AVISO_CATALOGO_GLOBAL")
    // La ventana es amplia y no una clase negada: el subtítulo es un template literal con
    // `${empresas.length}` adentro, así que la primera `}` aparece antes del aviso.
    expect(pagina).toMatch(/description=\{[\s\S]{0,400}?AVISO_CATALOGO_GLOBAL/)
    expect(AVISO_CATALOGO_GLOBAL).toContain("sidebar no lo filtra")
  })

  it("(a) (b) (d) NO APLICAN: la pantalla no filtra ni pagina", () => {
    const pagina = readFileSync(PAGINA, "utf8")
    expect(pagina).not.toContain("<FiltersBar")
    expect(pagina).not.toContain("<Pagination")
    // Contracara: el archivo que se está leyendo es el que se cree. Sin esto, un path mal armado
    // devolvería texto vacío y las dos aserciones de arriba pasarían sin mirar nada.
    expect(pagina).toContain("<EmpresasTable")
  })
})
