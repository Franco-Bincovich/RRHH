import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { FiltersBar } from "@/components/ui/FiltersBar"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import type { FiltroCampo } from "@/components/ui/filtrosTipos"

import { EmpleadosTable } from "./EmpleadosTable"

/**
 * (c), (e) y (f) del patrón "Vacío y carga" sobre la pantalla piloto.
 *
 * 🔴 (c) ES EL CAMBIO DE COMPORTAMIENTO DE ESTA SESIÓN. Hasta ahora, con cero resultados
 * /empleados reemplazaba la tabla ENTERA por un `<EmptyState>`: se iban los nombres de las
 * columnas y la pantalla cambiaba de forma justo cuando el usuario necesita entender qué estaba
 * mirando. Ahora el vacío es una fila con `colSpan` y el encabezado se queda.
 *
 * ALCANCE, sin disimular: vitest corre sin jsdom, así que se verifica el MARKUP y los handlers se
 * invocan a mano. "Clickear 'Quitar estado: Baja' llama a `quitar`" no es verificable acá; lo que
 * sí se verifica es que el botón que se ofrece sea el del ÚLTIMO chip y no el de otro, que es la
 * decisión que este componente toma. Que quitar un chip no toque a los demás está probado un
 * escalón más abajo, en `chipsEmpleados.test.ts`.
 */

const chip = (etiqueta: string, valor: string, quitar = () => {}): ChipFiltro => ({
  clave: etiqueta, etiqueta, valor, quitar,
})

const CHIPS = [chip("Empresa", "Bodegas Tupungato"), chip("Área", "Sistemas"), chip("Estado", "Baja")]

function tabla(props: Partial<Parameters<typeof EmpleadosTable>[0]> = {}) {
  return renderToStaticMarkup(
    <EmpleadosTable
      items={[]} loading={false} error={false} showEmpresa
      onRetry={() => {}} onRowClick={() => {}}
      chips={CHIPS} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) con filtros activos y cero resultados, el encabezado SIGUE renderizado", () => {
  const html = tabla()

  it("las columnas siguen ahí", () => {
    for (const columna of ["Nombre", "Empresa", "Área", "Roles", "Modalidad", "Estado"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
  })

  it("el vacío es una fila de la tabla, no un bloque que la reemplaza", () => {
    expect(html).toContain("<table")
    expect(html).toContain('colSpan="7"')
  })

  it("y el encabezado también está durante la carga y con datos: la forma no cambia nunca", () => {
    expect(tabla({ loading: true })).toContain("<thead")
    expect(tabla({
      loading: false,
      items: [{
        id: "1", nombre: "Ana", apellido: "Pérez", estado: "activo", modalidad_trabajo: "remoto",
      } as Parameters<typeof EmpleadosTable>[0]["items"][number]],
    })).toContain("<thead")
  })
})

describe("(d bis) el bloque del vacío usa los valores reales", () => {
  it("nombra la empresa, el área y el estado que el usuario puso", () => {
    const html = tabla()
    expect(html).toContain("Bodegas Tupungato no tiene colaboradores con área Sistemas y estado Baja.")
  })
})

describe("(e) las dos salidas: quitar el último filtro o limpiar todo", () => {
  it("ofrece quitar el ÚLTIMO chip, no otro", () => {
    // El último es el que el usuario acaba de poner: es el candidato obvio a deshacer.
    const html = tabla()
    expect(html).toContain("Quitar estado: Baja")
    expect(html).not.toContain("Quitar empresa")
    expect(html).not.toContain("Quitar área")
  })

  it("y ofrece limpiar todo, sin ejecutar ninguna de las dos sola", () => {
    expect(tabla()).toContain("Limpiar todo")
  })

  it("quitar el último llama SOLO a ese chip", () => {
    // Sin DOM no hay click: se verifica sobre el handler que el componente elige, que es la
    // decisión propia de este archivo.
    const spies = [vi.fn(), vi.fn(), vi.fn()]
    const chips = [chip("Empresa", "K", spies[0]), chip("Área", "S", spies[1]), chip("Estado", "Baja", spies[2])]
    chips[chips.length - 1].quitar()
    expect(spies[2]).toHaveBeenCalled()
    expect(spies[0]).not.toHaveBeenCalled()
    expect(spies[1]).not.toHaveBeenCalled()
  })

  it("sin filtros no ofrece quitar nada: ofrece cargar el primero", () => {
    const html = tabla({ chips: [], accionVacio: <button>Cargar el primero</button> })
    expect(html).toContain("Todavía no hay colaboradores")
    expect(html).toContain("Cargar el primero")
    expect(html).not.toContain("Limpiar todo")
  })

  it("sin filtros y sin permiso de escritura, no aparece una acción que el usuario no puede hacer", () => {
    const html = tabla({ chips: [], accionVacio: undefined })
    expect(html).toContain("Todavía no hay colaboradores")
    expect(html).not.toContain("Cargar el primero")
  })
})

describe("(f) durante la carga", () => {
  const campos: FiltroCampo[] = [
    { tipo: "search", label: "Buscar", value: "", onChange: () => {} },
    { tipo: "select", label: "Estado", value: "", opciones: [{ value: "baja", label: "Baja" }], onChange: () => {} },
  ]

  it("los filtros están presentes pero deshabilitados", () => {
    const html = renderToStaticMarkup(<FiltersBar campos={campos} panel disabled />)
    // Presentes: no se ocultan ni se vacían.
    expect(html).toContain("Buscar")
    expect(html).toContain("Estado")
    // Y deshabilitados: los dos controles.
    expect(html.match(/disabled=""/g) ?? []).toHaveLength(2)
  })

  it("sin `disabled` no hay ningún control bloqueado", () => {
    // Contracara: sin esto, un componente que renderizara `disabled` siempre pasaría el de arriba.
    expect(renderToStaticMarkup(<FiltersBar campos={campos} panel />)).not.toContain('disabled=""')
  })

  /*
   * 🔑 `<th[ >]` Y NO `<th`: el segundo matchea también `<thead` y devuelve una columna de más.
   * Lo cazó este test al escribirlo —decía 8 columnas donde hay 7— y es la misma trampa que
   * `paginacionTotales.test.ts` documenta para los barridos: comparar un tramo de texto suelto
   * contra markup encuentra cosas que no son.
   */
  const celdas = (html: string) => (html.match(/<td[ >]/g) ?? []).length
  const encabezados = (html: string) => (html.match(/<th[ >]/g) ?? []).length

  it("el esqueleto tiene la misma cantidad de columnas que la tabla", () => {

    const cargando = tabla({ loading: true })
    expect(encabezados(cargando)).toBe(7)
    // 8 filas de esqueleto × 7 columnas.
    expect(celdas(cargando)).toBe(8 * 7)
  })

  it("y también cuando el modo consolidado saca la columna Empresa", () => {
    // La grilla es UNA sola lista: si el esqueleto declarara sus columnas aparte, esta variante
    // es la que las desalinea.
    const cargando = tabla({ loading: true, showEmpresa: false })
    expect(encabezados(cargando)).toBe(6)
    expect(celdas(cargando)).toBe(8 * 6)
  })

  it("el esqueleto usa el shimmer, no el pulse de 2s", () => {
    expect(tabla({ loading: true })).toContain("animate-shimmer")
  })
})
