// Invariante list ↔ export en los wrappers del front.
//
// El backend ya está cubierto por tests/test_paridad_list_export.py, que compara los Query
// params de cada par de endpoints. Pero ese test no puede ver el otro lado del cable: un
// endpoint de export que acepta `empleado_id` y un wrapper de JS que nunca se lo manda pasan
// la paridad del backend y aun así descargan de más.
//
// Lo que fija este archivo es que el listado y el export de un mismo módulo traduzcan el MISMO
// objeto de filtros a los MISMOS query params. Por eso cada bloque compara las dos llamadas
// entre sí, no contra una lista escrita a mano: si mañana se suma un filtro a la traducción
// compartida, el test sigue valiendo sin tocarlo.
import { beforeEach, describe, expect, it, vi } from "vitest"

const { apiFetch, descargarArchivo } = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  descargarArchivo: vi.fn(),
}))

vi.mock("@/services/api", () => ({ apiFetch, descargarArchivo }))

import { exportarCapacitaciones, fetchAsignaciones as fetchCapacitaciones } from "@/services/capacitaciones"
import {
  exportarInventarioAsignaciones, exportarInventarioItems,
  fetchAsignaciones as fetchInventarioAsignaciones, fetchItems,
} from "@/services/inventario"

/** Query params con los que se llamó a apiFetch (el listado). */
function queryListado(): URLSearchParams {
  const path = apiFetch.mock.calls[0][0] as string
  return new URLSearchParams(path.split("?")[1] ?? "")
}

/** Query params con los que se llamó a descargarArchivo (el export), sin los vacíos. */
function queryExport(): Record<string, string> {
  const params = (descargarArchivo.mock.calls[0][4] ?? {}) as Record<string, string | undefined>
  return Object.fromEntries(Object.entries(params).filter(([, v]) => v)) as Record<string, string>
}

function headersExport(): Record<string, string> | undefined {
  return descargarArchivo.mock.calls[0][3] as Record<string, string> | undefined
}

/** Los params del listado, como objeto plano, para comparar contra los del export. */
function listadoComoObjeto(): Record<string, string> {
  return Object.fromEntries(queryListado().entries())
}

beforeEach(() => {
  apiFetch.mockReset().mockResolvedValue({ items: [], total: 0 })
  descargarArchivo.mockReset().mockResolvedValue(undefined)
})

describe("capacitaciones — asignaciones", () => {
  const filtros = {
    empresaIdOverride: "emp-1",
    empleadoId: "empleado-7",
    capacitacionId: "cap-3",
    estado: "completado",
    areaId: "area-9",
  }

  it("el export manda los cinco filtros, incluidos empleado y capacitación", async () => {
    await exportarCapacitaciones("excel", filtros)
    expect(queryExport()).toEqual({
      empleado_id: "empleado-7",
      capacitacion_id: "cap-3",
      estado: "completado",
      area_id: "area-9",
    })
    expect(headersExport()).toEqual({ "X-Empresa-Id": "emp-1" })
  })

  it("el listado y el export traducen el mismo objeto a los mismos params", async () => {
    await fetchCapacitaciones(filtros)
    await exportarCapacitaciones("excel", filtros)
    expect(queryExport()).toEqual(listadoComoObjeto())
  })

  it("sin filtros no manda params vacíos", async () => {
    await exportarCapacitaciones("pdf", {})
    expect(queryExport()).toEqual({})
    expect(headersExport()).toBeUndefined()
  })
})

describe("inventario — asignaciones", () => {
  const filtros = { empresaIdOverride: "emp-2", empleadoId: "empleado-4" }

  it("el export manda empleado_id", async () => {
    await exportarInventarioAsignaciones("csv", filtros)
    expect(queryExport()).toEqual({ empleado_id: "empleado-4" })
    expect(headersExport()).toEqual({ "X-Empresa-Id": "emp-2" })
  })

  it("el listado y el export traducen el mismo objeto a los mismos params", async () => {
    await fetchInventarioAsignaciones(filtros)
    await exportarInventarioAsignaciones("csv", filtros)
    expect(queryExport()).toEqual(listadoComoObjeto())
  })
})

describe("inventario — ítems", () => {
  const filtros = { empresaIdOverride: "emp-3", estado: "disponible" }

  it("el export manda estado", async () => {
    await exportarInventarioItems("word", filtros)
    expect(queryExport()).toEqual({ estado: "disponible" })
    expect(headersExport()).toEqual({ "X-Empresa-Id": "emp-3" })
  })

  it("el listado y el export traducen el mismo objeto a los mismos params", async () => {
    await fetchItems(filtros)
    await exportarInventarioItems("word", filtros)
    expect(queryExport()).toEqual(listadoComoObjeto())
  })
})

describe("la empresa viaja por header, no por query", () => {
  // Es la regla de todo el repo: empresa se resuelve en AuthMiddleware desde X-Empresa-Id.
  // Si alguna vez apareciera como query param, el backend la ignoraría en silencio.
  it("ni el listado ni el export la mandan como param", async () => {
    await fetchCapacitaciones({ empresaIdOverride: "emp-1" })
    await exportarCapacitaciones("excel", { empresaIdOverride: "emp-1" })
    expect(queryListado().get("empresa_id")).toBeNull()
    expect(queryExport()).not.toHaveProperty("empresa_id")
  })
})
