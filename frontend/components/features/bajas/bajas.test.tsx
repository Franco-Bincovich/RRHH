import { renderToStaticMarkup } from "react-dom/server"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { ChipFiltro } from "@/components/ui/filtrosChips"
import type { Empleado } from "@/types/empleado"

const { apiFetch, descargarArchivo } = vi.hoisted(() => ({
  apiFetch: vi.fn(), descargarArchivo: vi.fn(),
}))
vi.mock("@/services/api", () => ({ apiFetch, descargarArchivo }))

import { fetchEmpleados } from "@/services/empleados"

import { BajasTable } from "./BajasTable"
import { antiguedadAlEgreso, filtrosBajas } from "./_bajas"

/**
 * (a), (d) y (e) de /bajas.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * (a) se prueba en los TRES eslabones, igual que en próximos ingresos: la pantalla pide el orden,
 * el orden viaja como query param, y la tabla NO reordena. El padrón tiene el apellido y la
 * fecha desalineados a propósito — sin eso, un `.sort()` colado en el render daría el mismo
 * markup y el test no podría verlo.
 *
 * (d) tiene su CONTRACARA obligatoria: además de "la celda está vacía" se afirma que la fila con
 * motivo SÍ lo muestra. Con solo la primera mitad, una tabla que no renderizara nunca el motivo
 * pasaría en verde.
 *
 * 🔴 EL PADRÓN INCLUYE LA BAJA SIN FECHA DE EGRESO, que es la fila que el `NULLS FIRST` de
 * postgrest deja PRIMERA. Está en la posición 0 del array a propósito: así el test de orden
 * afirma que la tabla la deja donde llegó en vez de "arreglarla" mandándola al final.
 */

const chip = (etiqueta: string, valor: string, quitar = () => {}): ChipFiltro => ({
  clave: etiqueta, etiqueta, valor, quitar,
})

function baja(
  id: string, apellido: string, fecha_egreso: string | null, motivo_baja: string | null,
  fecha_ingreso = "2020-03-15",
): Empleado {
  return {
    id, nombre: "Ana", apellido, fecha_ingreso, fecha_egreso, motivo_baja, estado: "baja",
    empresa_nombre: "Bodegas Tupungato", area_nombre: "Sistemas",
  } as unknown as Empleado
}

const PADRON = [
  // Sin fecha: el backend la manda primera (NULLS FIRST) y la tabla la deja ahí.
  baja("0", "Ventura", null, null),
  baja("1", "Zapata", "2026-05-31", "renuncia"),          // se fue último, apellido último
  baja("2", "Molina", "2024-01-10", null),                // 🔑 el caso (d): baja sin motivo
  baja("3", "Acosta", "2021-06-30", "despido sin causa"),
]

function tabla(props: Partial<Parameters<typeof BajasTable>[0]> = {}) {
  return renderToStaticMarkup(
    <BajasTable
      items={PADRON} loading={false} error={false} showEmpresa
      onRetry={() => {}} onRowClick={() => {}} chips={[]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

beforeEach(() => {
  apiFetch.mockReset().mockResolvedValue({ items: [], total: 0 })
})

describe("(a) la lista sale ordenada por fecha de egreso descendente, no por apellido", () => {
  it("1. la pantalla pide el orden y el estado que la definen", () => {
    expect(filtrosBajas({}).orden).toBe("fecha_egreso_desc")
    expect(filtrosBajas({}).estado).toBe("baja")
  })

  it("2. los dos viajan al backend como query params", async () => {
    await fetchEmpleados({ page: 1, pageSize: 20, ...filtrosBajas({}) })
    const query = new URLSearchParams((apiFetch.mock.calls[0][0] as string).split("?")[1])
    expect(query.get("orden")).toBe("fecha_egreso_desc")
    expect(query.get("estado")).toBe("baja")
  })

  it("3. la tabla dibuja las filas en el MISMO orden en que le llegan", () => {
    const html = tabla()
    const posiciones = PADRON.map((e) => html.indexOf(e.apellido))
    expect(posiciones.every((p) => p >= 0), "faltó algún apellido en el markup").toBe(true)
    expect(posiciones).toEqual([...posiciones].sort((x, y) => x - y))
  })

  it("🔴 3 bis. la baja SIN fecha se queda arriba: el NULLS FIRST no se tapa en el cliente", () => {
    // Es una conducta declarada del backend (postgrest no expresa NULLS LAST) y está pineada con
    // un test allá. Reordenar acá ordenaría solo la página que llegó, y de paso escondería la
    // única señal de que a esa baja le falta el dato.
    const html = tabla()
    expect(html.indexOf("Ventura")).toBeLessThan(html.indexOf("Zapata"))
    // Y la fecha ausente se muestra como guion, no en blanco ni como "null".
    expect(html).not.toContain("null")
  })
})

describe("(d) una baja sin motivo muestra la celda vacía", () => {
  it("no dice 'Sin especificar' ni ningún relleno", () => {
    // El reporte de movimientos SÍ rellena, porque agrupa; acá cada fila es una persona, y
    // "Sin especificar" convertiría "no sabemos por qué se fue" en un motivo cargado.
    const html = tabla({ items: [PADRON[2]] })
    expect(html).not.toContain("Sin especificar")
    expect(html).not.toContain("—</td><td")  // tampoco el guion que sí usan fecha y antigüedad
  })

  it("y la fila que SÍ tiene motivo lo muestra: la contracara", () => {
    const html = tabla()
    expect(html).toContain("renuncia")
    expect(html).toContain("despido sin causa")
  })
})

describe("la antigüedad se mide al día del egreso, no a hoy", () => {
  it("cuenta de calendario entre ingreso y egreso", () => {
    expect(antiguedadAlEgreso({ fecha_ingreso: "2020-03-15", fecha_egreso: "2026-05-31" }))
      .toBe("6 años y 2 meses")
  })

  it("🔴 sin fecha de egreso NO se mide contra hoy: sería un número que crece todos los días", () => {
    expect(antiguedadAlEgreso({ fecha_ingreso: "2020-03-15", fecha_egreso: null })).toBe("—")
  })

  it("y con un egreso anterior al ingreso tampoco: es dato roto, no 'todavía no entró'", () => {
    expect(antiguedadAlEgreso({ fecha_ingreso: "2026-05-31", fecha_egreso: "2020-03-15" })).toBe("—")
  })
})

describe("(e) el vacío usa los valores reales de los filtros", () => {
  it("nombra la empresa como sujeto y el resto como condiciones", () => {
    const html = tabla({
      items: [],
      chips: [chip("Empresa", "Bodegas Tupungato"), chip("Área", "Sistemas")],
    })
    expect(html).toContain("Bodegas Tupungato no tiene bajas con área Sistemas.")
  })

  it("sin filtros dice que todavía no hay, y no ofrece quitar nada", () => {
    const html = tabla({ items: [], chips: [] })
    expect(html).toContain("Todavía no hay bajas")
    expect(html).not.toContain("Limpiar todo")
  })

  it("el encabezado sigue puesto en el vacío y en la carga", () => {
    for (const html of [tabla({ items: [] }), tabla({ loading: true })]) {
      expect(html).toContain("<thead")
      expect(html).toContain("Motivo")
      expect(html).toContain("Antigüedad")
    }
  })

  it("en modo consolidado la columna Empresa está, y con una empresa activa no", () => {
    expect((tabla({ loading: true }).match(/<th[ >]/g) ?? []).length).toBe(6)
    expect((tabla({ loading: true, showEmpresa: false }).match(/<th[ >]/g) ?? []).length).toBe(5)
  })
})
