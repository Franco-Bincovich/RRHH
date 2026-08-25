import { renderToStaticMarkup } from "react-dom/server"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { ChipFiltro } from "@/components/ui/filtrosChips"
import type { Empleado } from "@/types/empleado"

// vi.hoisted: vi.mock se iza por encima de los const, así que el doble se crea acá.
const { apiFetch, descargarArchivo } = vi.hoisted(() => ({
  apiFetch: vi.fn(), descargarArchivo: vi.fn(),
}))
vi.mock("@/services/api", () => ({ apiFetch, descargarArchivo }))

import { fetchEmpleados } from "@/services/empleados"

import { ProximosIngresosTable } from "./ProximosIngresosTable"
import { filtrosProximosIngresos, motivoNoSePuedeConfirmar, textoFaltan } from "./_proximosIngresos"

/**
 * (a) y (e) de /proximos-ingresos: que la lista salga ordenada por SU fecha y que el vacío hable
 * con los valores reales de los filtros. (b) y (c) —el acto de confirmar— viven en
 * `components/features/empleados/confirmarIngreso.test.ts`, que es donde está la función.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * (a) se prueba en LOS TRES ESLABONES de la cadena, porque romper cualquiera de los tres deja la
 * pantalla ordenada por apellido y ninguno de los otros dos lo nota:
 *   1. la pantalla PIDE el orden (`filtrosProximosIngresos`) — si alguien saca la clave, rojo;
 *   2. el orden VIAJA como query param (`fetchEmpleados` con `apiFetch` falseado) — si alguien
 *      saca el `params.set("orden", …)`, el objeto sigue estando y el backend nunca se entera;
 *   3. la tabla NO REORDENA lo que le llega — el padrón tiene los apellidos al revés que las
 *      fechas, así que un `.sort()` por apellido colado en el render invierte el markup y rojea.
 * Sin el punto 3 el test más plausible de todos ("ordena bien") pasaría con un `.sort()` local
 * que rompe la paginación en silencio.
 *
 * (e) usa `textoVacio` de verdad a través del componente, no una constante escrita acá: el texto
 * sale de los chips que la página ya le pasa a `<FiltersBar>`, así que si el sustantivo o el
 * sujeto se cambian, esto lo dice.
 */

const chip = (etiqueta: string, valor: string, quitar = () => {}): ChipFiltro => ({
  clave: etiqueta, etiqueta, valor, quitar,
})

/**
 * 🔑 EL APELLIDO VA AL REVÉS QUE LA FECHA, a propósito: es lo único que hace que el punto 3 de
 * arriba pueda fallar. Con apellidos ya alfabéticos, una tabla que ordenara por apellido daría
 * exactamente el mismo markup que una que no ordena nada.
 */
function emp(id: string, apellido: string, fecha_ingreso: string): Empleado {
  return {
    id, nombre: "Ana", apellido, fecha_ingreso, estado: "preingreso",
    empresa_nombre: "Bodegas Tupungato", area_nombre: "Sistemas",
  } as unknown as Empleado
}

const PADRON = [
  emp("1", "Zapata", "2026-09-01"),   // entra primero, apellido último
  emp("2", "Molina", "2026-10-15"),
  emp("3", "Acosta", "2026-12-20"),   // entra último, apellido primero
]

function tabla(props: Partial<Parameters<typeof ProximosIngresosTable>[0]> = {}) {
  return renderToStaticMarkup(
    <ProximosIngresosTable
      items={PADRON} loading={false} error={false} showEmpresa
      onRetry={() => {}} onRowClick={() => {}} chips={[]} onLimpiarTodo={() => {}}
      activandoId={null} onActivar={() => {}}
      {...props}
    />,
  )
}

beforeEach(() => {
  apiFetch.mockReset().mockResolvedValue({ items: [], total: 0 })
})

describe("(a) la lista sale ordenada por fecha de ingreso, no por apellido", () => {
  it("1. la pantalla pide el orden ascendente por fecha de ingreso", () => {
    expect(filtrosProximosIngresos({}).orden).toBe("fecha_ingreso_asc")
  })

  it("1 bis. y pide SOLO los preingresos: sin `estado` el backend ni siquiera los trae", () => {
    // El default de `filtro_estado` los EXCLUYE. Sin esta clave la pantalla saldría vacía
    // teniendo preingresos cargados, que es peor que salir desordenada.
    expect(filtrosProximosIngresos({}).estado).toBe("preingreso")
  })

  it("2. el orden viaja al backend como query param", async () => {
    await fetchEmpleados({ page: 1, pageSize: 20, ...filtrosProximosIngresos({}) })
    const query = new URLSearchParams((apiFetch.mock.calls[0][0] as string).split("?")[1])
    expect(query.get("orden")).toBe("fecha_ingreso_asc")
    expect(query.get("estado")).toBe("preingreso")
  })

  it("3. la tabla dibuja las filas en el MISMO orden en que le llegan", () => {
    const html = tabla()
    const posiciones = PADRON.map((e) => html.indexOf(e.apellido))
    expect(posiciones.every((p) => p >= 0), "faltó algún apellido en el markup").toBe(true)
    // Estrictamente creciente = el orden del array. Un `.sort()` por apellido lo invierte.
    expect(posiciones).toEqual([...posiciones].sort((x, y) => x - y))
    expect(html.indexOf("Zapata")).toBeLessThan(html.indexOf("Acosta"))
  })
})

describe("la cuenta regresiva", () => {
  it("dice los casos frecuentes en palabras, no 'en 0 días'", () => {
    expect(textoFaltan(0).texto).toBe("Hoy")
    expect(textoFaltan(1).texto).toBe("Mañana")
    expect(textoFaltan(12).texto).toBe("En 12 días")
  })

  it("destaca SOLO lo que ya tendría que haber pasado", () => {
    // Es la única fila sobre la que hay algo que hacer, y la única que el backend deja activar.
    expect(textoFaltan(0).destacado).toBe(true)
    expect(textoFaltan(-3).destacado).toBe(true)
    expect(textoFaltan(-3).texto).toBe("Hace 3 días")
    expect(textoFaltan(14).destacado).toBe(false)
  })
})

describe("(e) el vacío usa los valores reales de los filtros", () => {
  it("nombra la empresa como sujeto y el resto como condiciones", () => {
    const html = tabla({
      items: [],
      chips: [chip("Empresa", "Bodegas Tupungato"), chip("Área", "Sistemas")],
    })
    expect(html).toContain("Bodegas Tupungato no tiene próximos ingresos con área Sistemas.")
  })

  it("sin filtros dice que todavía no hay, y no ofrece quitar nada", () => {
    const html = tabla({ items: [], chips: [] })
    expect(html).toContain("Todavía no hay próximos ingresos")
    expect(html).not.toContain("Limpiar todo")
  })

  it("con filtros ofrece quitar el ÚLTIMO chip y limpiar todo", () => {
    const html = tabla({ items: [], chips: [chip("Empresa", "K"), chip("Área", "Sistemas")] })
    expect(html).toContain("Quitar área: Sistemas")
    expect(html).toContain("Limpiar todo")
  })

  it("el encabezado sigue puesto en el vacío y en la carga: la pantalla no cambia de forma", () => {
    for (const html of [tabla({ items: [] }), tabla({ loading: true })]) {
      expect(html).toContain("<thead")
      expect(html).toContain("Ingresa")
      expect(html).toContain("Faltan")
    }
  })
})

describe("el botón de escribir se gatea; el link de leer no", () => {
  it("sin `onActivar` no hay botón de confirmar, pero la columna y el legajo siguen", () => {
    /*
     * Un botón que siempre termina en 403 es peor que no ofrecerlo. Pero el acceso a la ficha es
     * LECTURA: ocultar la columna entera le sacaba a `gerencia_lectura` la referencia de qué
     * está mirando.
     *
     * 🔑 ESE ACCESO CAMBIÓ DE LUGAR EN LA MISMA TANDA. Primero se agregó como un link "Ver
     * legajo" en la columna de acciones —la pantalla no tenía NINGUNA forma de abrir la ficha,
     * pese a que el error de confirmar manda a "corregí la fecha en su legajo"— y después, al
     * unificar el patrón de /empresas, el NOMBRE de la columna 1 pasó a ser el link. Con los dos
     * eran dos accesos al mismo lugar en la misma fila; quedó el de la identidad, que es donde
     * el usuario lo busca. Lo que se afirma es el acceso, no dónde estaba.
     */
    const html = tabla({ onActivar: undefined })
    expect(html).not.toContain("Confirmar ingreso")
    expect((html.match(/href="\/empleados\//g) ?? []).length).toBe(PADRON.length)
    expect((html.match(/<th[ >]/g) ?? []).length).toBe(6)
  })

  it("con `onActivar` hay un botón por fila", () => {
    const html = tabla()
    expect((html.match(/Confirmar ingreso/g) ?? []).length).toBe(PADRON.length)
    expect((html.match(/<th[ >]/g) ?? []).length).toBe(6)
  })

  it("la fila que se está confirmando es la única deshabilitada", () => {
    // Con un `activando: boolean` en vez del id, se apagarían los tres botones a la vez.
    const html = tabla({ activandoId: "2" })
    expect(html).toContain("Confirmando...")
    expect((html.match(/Confirmando\.\.\./g) ?? []).length).toBe(1)
  })
})

describe("no se ofrece confirmar un ingreso que el backend va a rechazar", () => {
  /**
   * 🔴 INVIERTE LA DECISIÓN QUE ESTABA ESCRITA EN `ProximosIngresosTable` ("EL BOTÓN NO SE
   * DESHABILITA POR FECHA"). El porqué está en `motivoNoSePuedeConfirmar`; acá se fija el
   * comportamiento. Lo que lo motivó, medido: las SEIS filas de la pantalla tenían fecha futura
   * y las seis daban 400.
   *
   * ⚠️ Estos casos prueban la FUNCIÓN y no el render, a propósito: la tabla arma su padrón con
   * fechas fijas y "futuro" depende de cuándo corra la suite, así que un test de markup se
   * volvería verde o rojo según el día. `diasHasta` ya acepta el "hoy" por parámetro justamente
   * para esto.
   */
  it("con fecha futura hay motivo, y dice la fecha Y la salida", () => {
    const motivo = motivoNoSePuedeConfirmar(14, "2026-09-08")
    expect(motivo).toContain("2026-09-08")
    // La segunda mitad es la que resuelve el caso real: alguien que ya está trabajando.
    expect(motivo).toContain("corregí la fecha en su legajo")
  })

  it("hoy y los días ya pasados NO tienen motivo: son justo las filas que hay que confirmar", () => {
    expect(motivoNoSePuedeConfirmar(0, "2026-08-25")).toBeNull()
    expect(motivoNoSePuedeConfirmar(-3, "2026-08-22")).toBeNull()
  })

  it("una fecha ilegible NO bloquea", () => {
    // Bloquear por una fecha que no se pudo leer dejaría la fila muerta sin ninguna salida
    // desde la pantalla. El backend es el que sabe.
    expect(motivoNoSePuedeConfirmar(null, "")).toBeNull()
  })
})

describe("desde acá se llega al legajo", () => {
  it("cada fila tiene un link real a la ficha, no solo el click de la fila", () => {
    /**
     * 🔴 El propio mensaje de error manda a "corregí la fecha en su legajo" y hasta el
     * 25/8/2026 esta pantalla no tenía cómo abrirlo: la fila navegaba con `onClick`, que no se
     * ve, no se alcanza por teclado y no se puede abrir en una pestaña nueva. El link vive en el
     * NOMBRE, que es el patrón de `EmpresasTable` — un `<tr>` no puede ser un `<a>`.
     */
    const html = tabla()
    for (const emp of PADRON) {
      expect(html).toContain(`href="/empleados/${emp.id}"`)
    }
  })
})
