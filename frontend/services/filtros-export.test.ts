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

import { exportarEmpleados, fetchEmpleados } from "@/services/empleados"
import { exportarCapacitaciones, fetchAsignaciones as fetchCapacitaciones } from "@/services/capacitaciones"
import { exportarAusencias, fetchAusencias } from "@/services/ausencias"
import {
  exportarInventarioAsignaciones, exportarInventarioItems,
  fetchAsignaciones as fetchInventarioAsignaciones, fetchItems,
} from "@/services/inventario"
import { fetchProyectos } from "@/services/proyectos"
import { exportarVacaciones, fetchVacaciones } from "@/services/vacaciones"

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

/** El segundo argumento de apiFetch (headers del listado). */
function initListado(): { headers?: Record<string, string> } | undefined {
  return apiFetch.mock.calls[0][1] as { headers?: Record<string, string> } | undefined
}

/**
 * Los params del listado, como objeto plano, para comparar contra los del export.
 *
 * 🔴 `page`/`page_size` se SACAN, y es la única diferencia legítima: el export NO se pagina, por
 * diseño. Si viajaran al archivo, saldría con una página de 20 filas en vez del listado entero —
 * sin error y sin aviso. Es la misma excepción que declara `test_paridad_list_export.py` del lado
 * del backend (`_SOLO_LISTADO`), y está acá para que las dos puntas digan lo mismo.
 *
 * ⚠️ Se sacan SOLO esas dos. Cualquier otro param que el listado mande y el export no, sigue
 * rompiendo estos tests, que es exactamente lo que tienen que hacer.
 */
const SOLO_LISTADO = ["page", "page_size"]

function listadoComoObjeto(): Record<string, string> {
  const params = queryListado()
  for (const k of SOLO_LISTADO) params.delete(k)
  return Object.fromEntries(params.entries())
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
  const filtros = { empresaIdOverride: "emp-3", estado: "disponible", areaId: "area-9" }

  it("el export manda estado y area_id", async () => {
    await exportarInventarioItems("word", filtros)
    expect(queryExport()).toEqual({ estado: "disponible", area_id: "area-9" })
    expect(headersExport()).toEqual({ "X-Empresa-Id": "emp-3" })
  })

  it("el listado manda area_id con el MISMO nombre que espera el backend", async () => {
    // `areaId` en el objeto de filtros, `area_id` en el cable: la traducción vive una sola vez
    // en queryItems. Si divergiera, el backend ignoraría el filtro y devolvería todo.
    await fetchItems(filtros)
    expect(queryListado().get("area_id")).toBe("area-9")
  })

  it("el listado y el export traducen el mismo objeto a los mismos params", async () => {
    await fetchItems(filtros)
    await exportarInventarioItems("word", filtros)
    expect(queryExport()).toEqual(listadoComoObjeto())
  })

  it("sin área no manda el param: un area_id vacío filtraría por nada", async () => {
    // Contrapeso del primero: sin esto, mandar SIEMPRE area_id pasaría los de arriba.
    await fetchItems({ estado: "disponible" })
    expect(queryListado().has("area_id")).toBe(false)
  })
})

describe("vacaciones — con rango de fechas", () => {
  const filtros = {
    empresaIdOverride: "emp-1", areaId: "area-1", empleadoId: "empleado-2",
    estado: "tomada", fechaDesde: "2026-03-01", fechaHasta: "2026-03-31",
  }

  it("el export manda los seis filtros, incluido el rango", async () => {
    await exportarVacaciones("excel", filtros)
    expect(queryExport()).toEqual({
      area_id: "area-1", empleado_id: "empleado-2", estado: "tomada",
      fecha_desde: "2026-03-01", fecha_hasta: "2026-03-31",
    })
  })

  it("el listado y el export traducen el mismo objeto a los mismos params", async () => {
    await fetchVacaciones(filtros)
    await exportarVacaciones("excel", filtros)
    const { page, page_size, ...listado } = listadoComoObjeto()  // el export no pagina
    expect(queryExport()).toEqual(listado)
  })

  it("un rango abierto manda solo la cota que tiene", async () => {
    await exportarVacaciones("excel", { fechaDesde: "2026-03-01" })
    expect(queryExport()).toEqual({ fecha_desde: "2026-03-01" })
  })

  it("sin rango no manda ninguna cota", async () => {
    await exportarVacaciones("excel", { estado: "tomada" })
    expect(queryExport()).toEqual({ estado: "tomada" })
  })
})

describe("ausencias — con rango de fechas", () => {
  const filtros = {
    empresaIdOverride: "emp-1", areaId: "area-1", tipoId: "tipo-3",
    empleadoId: "empleado-2", fechaDesde: "2026-03-01", fechaHasta: "2026-03-31",
  }

  it("el export manda los seis filtros, incluido el rango", async () => {
    await exportarAusencias("csv", filtros)
    expect(queryExport()).toEqual({
      area_id: "area-1", tipo_id: "tipo-3", empleado_id: "empleado-2",
      fecha_desde: "2026-03-01", fecha_hasta: "2026-03-31",
    })
  })

  it("el listado y el export traducen el mismo objeto a los mismos params", async () => {
    await fetchAusencias(filtros)
    await exportarAusencias("csv", filtros)
    const { page, page_size, ...listado } = listadoComoObjeto()
    expect(queryExport()).toEqual(listado)
  })

  it("un rango abierto manda solo la cota que tiene", async () => {
    await exportarAusencias("csv", { fechaHasta: "2026-03-31" })
    expect(queryExport()).toEqual({ fecha_hasta: "2026-03-31" })
  })
})

describe("empleados — es_lider es un booleano de tres estados", () => {
  // `false` es un filtro válido (solo NO líderes), no un vacío. Si en algún momento se
  // normalizara con `|| undefined` como los strings, "Solo no líderes" dejaría de filtrar
  // y devolvería la lista completa — sin error y sin que se note.
  it("true se manda como 'true'", async () => {
    await fetchEmpleados({ page: 1, pageSize: 20, esLider: true })
    expect(queryListado().get("es_lider")).toBe("true")
  })

  it("false se manda como 'false', no se descarta", async () => {
    await fetchEmpleados({ page: 1, pageSize: 20, esLider: false })
    expect(queryListado().get("es_lider")).toBe("false")
  })

  it("undefined no manda el param", async () => {
    await fetchEmpleados({ page: 1, pageSize: 20 })
    expect(queryListado().has("es_lider")).toBe(false)
  })

  it("el export manda los mismos tres estados", async () => {
    await exportarEmpleados({ formato: "excel", esLider: false })
    expect(queryExport()).toEqual({ es_lider: "false" })
  })

  it("el export sin el filtro no manda el param", async () => {
    await exportarEmpleados({ formato: "excel", estado: "activo" })
    expect(queryExport()).toEqual({ estado: "activo" })
  })

  it("se compone con los otros filtros, no los pisa", async () => {
    await exportarEmpleados({ formato: "excel", esLider: true, estado: "activo", areaId: "area-1", search: "ana" })
    expect(queryExport()).toEqual({
      es_lider: "true", estado: "activo", area_id: "area-1", search: "ana",
    })
  })
})

describe("empleados — sin_manager, el destino de la alerta agregada del dashboard", () => {
  // Mismo tri-estado que es_lider, y el mismo modo de falla si alguien lo normalizara con
  // `|| undefined`: "Con superior asignado" devolvería la lista entera.
  // El nombre del param es parte del contrato: la alerta linkea a /empleados?sin_manager=true,
  // y el hook de filtros siembra el select desde esa misma clave.
  it("true se manda como 'true'", async () => {
    await fetchEmpleados({ page: 1, pageSize: 20, sinManager: true })
    expect(queryListado().get("sin_manager")).toBe("true")
  })

  it("false se manda como 'false', no se descarta", async () => {
    await fetchEmpleados({ page: 1, pageSize: 20, sinManager: false })
    expect(queryListado().get("sin_manager")).toBe("false")
  })

  it("undefined no manda el param", async () => {
    await fetchEmpleados({ page: 1, pageSize: 20 })
    expect(queryListado().has("sin_manager")).toBe(false)
  })

  it("el listado y el export traducen el mismo objeto a los mismos params", async () => {
    const filtros = { sinManager: true, estado: "activo", areaId: "area-1" }
    await fetchEmpleados({ page: 1, pageSize: 20, ...filtros })
    await exportarEmpleados({ formato: "excel", ...filtros })
    // page/page_size quedan fuera a propósito: el export NO se pagina (es la excepción
    // declarada del invariante, la misma que exceptúa tests/test_paridad_list_export.py).
    const { page: _p, page_size: _ps, ...listadoSinPaginado } = listadoComoObjeto()
    expect(queryExport()).toEqual(listadoSinPaginado)
  })
})

describe("inventario — asignaciones con área", () => {
  const filtros = { empresaIdOverride: "emp-2", empleadoId: "empleado-4", areaId: "area-7" }

  it("el export manda empleado y área", async () => {
    await exportarInventarioAsignaciones("csv", filtros)
    expect(queryExport()).toEqual({ empleado_id: "empleado-4", area_id: "area-7" })
  })

  it("el listado y el export traducen el mismo objeto a los mismos params", async () => {
    await fetchInventarioAsignaciones(filtros)
    await exportarInventarioAsignaciones("csv", filtros)
    expect(queryExport()).toEqual(listadoComoObjeto())
  })

  it("solo área también viaja", async () => {
    await fetchInventarioAsignaciones({ areaId: "area-7" })
    expect(queryListado().get("area_id")).toBe("area-7")
  })
})

describe("proyectos — área y empresa", () => {
  it("el área viaja como query param", async () => {
    await fetchProyectos({ areaId: "area-7", estado: "activo" })
    const q = queryListado()
    expect(q.get("area_id")).toBe("area-7")
    expect(q.get("estado")).toBe("activo")
  })

  it("la empresa viaja por header, no por query", async () => {
    await fetchProyectos({ empresaIdOverride: "emp-9", areaId: "area-7" })
    expect(queryListado().has("empresa_id")).toBe(false)
    expect(initListado()?.headers).toEqual({ "X-Empresa-Id": "emp-9" })
  })

  it("sin filtros no manda más params que la paginación", async () => {
    // El listado SIEMPRE manda `page`/`page_size` desde que pagina — no son filtros y por eso se
    // descuentan. Lo que este test cuida es que un filtro vacío no viaje como param vacío.
    await fetchProyectos()
    expect(listadoComoObjeto()).toEqual({})
  })
})

describe("proyecto — el filtro llega a los cuatro módulos y a sus exports", () => {
  it("empleados: listado y export", async () => {
    await fetchEmpleados({ page: 1, pageSize: 20, proyectoId: "proy-1" })
    expect(queryListado().get("proyecto_id")).toBe("proy-1")
    await exportarEmpleados({ formato: "excel", proyectoId: "proy-1" })
    expect(queryExport()).toEqual({ proyecto_id: "proy-1" })
  })

  it("vacaciones: el mismo objeto va a los dos", async () => {
    const filtros = { proyectoId: "proy-1", estado: "tomada" }
    await fetchVacaciones(filtros)
    await exportarVacaciones("excel", filtros)
    const { page, page_size, ...listado } = listadoComoObjeto()
    expect(queryExport()).toEqual(listado)
    expect(queryExport().proyecto_id).toBe("proy-1")
  })

  it("ausencias: el mismo objeto va a los dos", async () => {
    const filtros = { proyectoId: "proy-1", tipoId: "tipo-1" }
    await fetchAusencias(filtros)
    await exportarAusencias("csv", filtros)
    const { page, page_size, ...listado } = listadoComoObjeto()
    expect(queryExport()).toEqual(listado)
  })

  it("sin proyecto no manda el param", async () => {
    await fetchEmpleados({ page: 1, pageSize: 20 })
    expect(queryListado().has("proyecto_id")).toBe(false)
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
