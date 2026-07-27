// Contrato HTTP de fetchEmpleados / exportarEmpleados tras migrarlas a objeto de opciones.
// Lo que fija este test es que el objeto de opciones se traduzca a los MISMOS query params y
// headers de siempre: `page`, `page_size`, `search`, `estado`, `area_id` y `X-Empresa-Id`.
//
// Antes las dos recibían cuatro `string | undefined` posicionales EN DISTINTO ORDEN
// (fetch: search, estado, empresa, area · export: empresa, search, estado, area), así que
// copiar argumentos de una a la otra compilaba y mandaba el filtro cruzado. El último bloque
// del archivo es justamente el que verifica que hoy el mismo objeto cae en el mismo lugar
// en las dos funciones.
import { beforeEach, describe, expect, it, vi } from "vitest"

// vi.hoisted: vi.mock se iza por encima de los const, así que los dobles se crean acá.
const { apiFetch, descargarArchivo } = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  descargarArchivo: vi.fn(),
}))

vi.mock("@/services/api", () => ({ apiFetch, descargarArchivo }))

import { exportarEmpleados, fetchEmpleados } from "@/services/empleados"

/** Query params con los que se llamó a apiFetch, ya parseados. */
function queryDeFetch(): URLSearchParams {
  const path = apiFetch.mock.calls[0][0] as string
  return new URLSearchParams(path.split("?")[1] ?? "")
}

function initDeFetch(): { headers?: Record<string, string> } {
  return apiFetch.mock.calls[0][1] as { headers?: Record<string, string> }
}

beforeEach(() => {
  apiFetch.mockReset().mockResolvedValue({ items: [], total: 0 })
  descargarArchivo.mockReset().mockResolvedValue(undefined)
})

describe("fetchEmpleados — objeto de opciones → query params", () => {
  it("manda los cuatro filtros en su param propio, con page y page_size", async () => {
    await fetchEmpleados({
      page: 3, pageSize: 20, search: "ana", estado: "activo",
      empresaId: "emp-1", areaId: "area-9",
    })
    const q = queryDeFetch()
    expect(apiFetch.mock.calls[0][0]).toMatch(/^\/api\/empleados\?/)
    expect(q.get("page")).toBe("3")
    expect(q.get("page_size")).toBe("20")
    expect(q.get("search")).toBe("ana")
    expect(q.get("estado")).toBe("activo")
    expect(q.get("area_id")).toBe("area-9")
    // la empresa NO es query param: viaja por header
    expect(q.has("empresa_id")).toBe(false)
    expect(initDeFetch().headers).toEqual({ "X-Empresa-Id": "emp-1" })
  })

  it("sin opcionales, la query trae solo page y page_size y no hay header de empresa", async () => {
    await fetchEmpleados({ page: 1, pageSize: 100 })
    const q = queryDeFetch()
    expect([...q.keys()]).toEqual(["page", "page_size"])
    expect(q.has("search")).toBe(false)
    expect(q.has("estado")).toBe(false)
    expect(q.has("area_id")).toBe(false)
    expect(initDeFetch()).toEqual({}) // sin headers: manda el selector del sidebar
  })

  it("los strings vacíos no llegan como filtro (mismo guard que antes)", async () => {
    await fetchEmpleados({ page: 1, pageSize: 50, search: "", estado: "", areaId: "" })
    const q = queryDeFetch()
    expect([...q.keys()]).toEqual(["page", "page_size"])
  })

  it('empresaId "todas" viaja tal cual en el header (el backend lo lee como consolidado)', async () => {
    await fetchEmpleados({ page: 1, pageSize: 200, estado: "activo", empresaId: "todas" })
    expect(initDeFetch().headers).toEqual({ "X-Empresa-Id": "todas" })
  })
})

describe("exportarEmpleados — objeto de opciones → params de descarga", () => {
  it("pasa formato, headers y los filtros con los nombres del backend", async () => {
    await exportarEmpleados({
      formato: "excel", search: "ana", estado: "activo",
      empresaId: "emp-1", areaId: "area-9",
    })
    expect(descargarArchivo).toHaveBeenCalledWith(
      "/api/empleados/exportar",
      "excel",
      "empleados",
      { "X-Empresa-Id": "emp-1" },
      { search: "ana", estado: "activo", area_id: "area-9" },
    )
  })

  it("sin opcionales no manda headers y deja los filtros en undefined", async () => {
    await exportarEmpleados({ formato: "pdf" })
    expect(descargarArchivo).toHaveBeenCalledWith(
      "/api/empleados/exportar",
      "pdf",
      "empleados",
      undefined,
      { search: undefined, estado: undefined, area_id: undefined },
    )
  })

  it('empresaId "todas" viaja tal cual en el header', async () => {
    await exportarEmpleados({ formato: "csv", empresaId: "todas" })
    expect(descargarArchivo.mock.calls[0][3]).toEqual({ "X-Empresa-Id": "todas" })
  })
})

describe("las dos funciones interpretan el MISMO objeto igual (la trampa vieja)", () => {
  it("search, estado, empresaId y areaId caen en el mismo lugar en fetch y en export", async () => {
    const filtros = { search: "perez", estado: "baja", empresaId: "emp-7", areaId: "area-2" }
    await fetchEmpleados({ page: 1, pageSize: 10, ...filtros })
    await exportarEmpleados({ formato: "excel", ...filtros })

    const q = queryDeFetch()
    const [, , , headersExport, paramsExport] = descargarArchivo.mock.calls[0] as [
      string, string, string, Record<string, string>, Record<string, string | undefined>,
    ]
    expect(q.get("search")).toBe(paramsExport.search)
    expect(q.get("estado")).toBe(paramsExport.estado)
    expect(q.get("area_id")).toBe(paramsExport.area_id)
    expect(initDeFetch().headers).toEqual(headersExport)
  })
})
