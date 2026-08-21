import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { PeriodoList } from "./PeriodoList"

/**
 * El patrón del bloque B sobre /periodos: **otro caso sin filtros** —`GET /api/periodos` no acepta
 * un solo Query; el recorte por empresa lo hace el header del sidebar— así que (a), (b) y (d) NO
 * APLICAN y este archivo lo dice en vez de simularlos.
 *
 * Lo que sí se verifica es (c) y la decisión propia de esta pantalla: **el vacío lleva copy
 * propio**, porque el genérico del patrón sería falso para quien la mira.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · que el vacío volviera a ser un `<p>` afuera de la tabla: desaparece `<thead>`.
 *   · que alguien "unificara" el copy usando `TablaVacia`: la pantalla pasaría a decirle a
 *     `gerencia_lectura` que cargue el primer período, cosa que no puede hacer — y perdería lo
 *     único útil que el vacío tiene para decir.
 *   · que "Cerrado" volviera a `variant="default"`: reaparece `bg-primary` en una celda de datos.
 */

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "periodos", "page.tsx")

const PERIODOS = [
  {
    id: "p1", empresa_id: "e1", modulo: "vacaciones", desde: "2026-01-01", hasta: "2026-01-31",
    estado: "cerrado", cerrado_por: "u1", cerrado_at: "2026-02-01T10:00:00Z",
    reabierto_por: null, reabierto_at: null,
  },
  {
    id: "p2", empresa_id: "e1", modulo: null, desde: "2025-12-01", hasta: "2025-12-31",
    estado: "reabierto", cerrado_por: "u1", cerrado_at: "2026-01-02T10:00:00Z",
    reabierto_por: "u1", reabierto_at: "2026-01-20T10:00:00Z",
  },
] as Parameters<typeof PeriodoList>[0]["periodos"]

function tabla(props: Partial<Parameters<typeof PeriodoList>[0]> = {}) {
  return renderToStaticMarkup(
    <PeriodoList
      periodos={[]} loading={false} error={false} canWrite
      nombreUsuario={() => "Ana Pérez"} onRetry={() => {}} onReabrir={() => {}}
      {...props}
    />,
  )
}

describe("(c) el encabezado sigue puesto en los tres estados", () => {
  it("con datos, y un período sin módulo se lee 'Todos los módulos'", () => {
    const html = tabla({ periodos: PERIODOS })
    expect(html).toContain("<thead")
    for (const columna of ["Módulo", "Desde", "Hasta", "Estado", "Detalle"]) {
      expect(html, `desapareció la columna ${columna}`).toContain(columna)
    }
    expect(html).toContain("Todos los módulos")
  })

  it("vacío: el bloque es una fila de la tabla, no un `<p>` que la reemplaza", () => {
    const html = tabla()
    expect(html).toContain("<thead")
    expect(html).toContain("<table")
    expect(html).toContain('colSpan="6"')
    // Y queda fuera del hover de datos: no es un registro que se pueda abrir.
    expect(html).toContain("data-vacio")
  })

  it("cargando: el esqueleto tiene la MISMA cantidad de columnas que la tabla", () => {
    const cargando = tabla({ loading: true })
    expect(cargando).toContain("<thead")
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(6)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 6)
    expect(cargando).toContain("animate-shimmer")
    // Sin permiso de escritura no hay nada que reabrir: la columna de acciones no existe, ni en
    // el encabezado ni en el esqueleto.
    const sinPermiso = tabla({ loading: true, canWrite: false })
    expect((sinPermiso.match(/<th[ >]/g) ?? []).length).toBe(5)
    expect((sinPermiso.match(/<td[ >]/g) ?? []).length).toBe(8 * 5)
  })
})

describe("🔴 el vacío lleva COPY PROPIO, no el genérico de textoVacio()", () => {
  it("dice qué SIGNIFICA que no haya ninguno, no que falte cargar el primero", () => {
    /*
     * Dos motivos, los dos verificados acá:
     *   · un período no se "carga", se CIERRA, y sólo `admin_rrhh` puede hacerlo — para
     *     `gerencia_lectura` la frase genérica es una instrucción que no puede seguir;
     *   · la ausencia acá significa algo concreto y útil: no hay ninguna restricción de fecha.
     */
    const html = tabla()
    expect(html).toContain("Todavía no hay períodos cerrados")
    expect(html).toContain("cualquier registro se puede cargar y editar sin restricción de fecha")
    expect(html).not.toContain("Cuando se cargue el primero")
  })

  it("y el copy es el mismo con y sin permiso de escritura: la frase no depende del rol", () => {
    // Es lo que la hace segura: no hay una versión que le hable a alguien que no puede actuar.
    expect(tabla({ canWrite: false })).toContain("sin restricción de fecha")
  })
})

describe("🔴 el badge de estado no es azul, y su semántica es la contraintuitiva", () => {
  it("'Cerrado' es el control PUESTO (éxito) y 'Reabierto' el que pide atención (warning)", () => {
    const html = tabla({ periodos: PERIODOS })
    expect(html).toContain("Cerrado")
    expect(html).toContain("Reabierto")
    expect(html).toContain("bg-success-wash")
    expect(html).toContain("bg-warning-wash")
    expect(html).not.toContain("bg-primary")
  })

  it("la acción de reabrir sólo aparece sobre un período cerrado", () => {
    const html = tabla({ periodos: PERIODOS })
    expect(html).toContain("Reabrir el período de 2026-01-01 a 2026-01-31")
    // El que ya está reabierto no ofrece reabrirse otra vez.
    expect(html).not.toContain("Reabrir el período de 2025-12-01 a 2025-12-31")
  })
})

describe("(a) (b) (d) NO APLICAN: la pantalla no filtra ni pagina", () => {
  it("la página no monta <FiltersBar> ni <Pagination>, y eso es lo correcto", () => {
    // `GET /api/periodos` no acepta ningún Query y devuelve la lista entera de la empresa activa.
    // Si algún día acepta filtros, ESTE test es el que hay que dar vuelta.
    const pagina = readFileSync(PAGINA, "utf8")
    expect(pagina).not.toContain("<FiltersBar")
    expect(pagina).not.toContain("<Pagination")
    // Contracara: el archivo leído es el que se cree.
    expect(pagina).toContain("<PeriodoList")
  })
})
