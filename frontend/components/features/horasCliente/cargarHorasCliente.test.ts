import { afterEach, describe, expect, it, vi } from "vitest"

/**
 * La carga de la vista apaga el loading SIEMPRE.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * Que `fetchHorasPorCliente` no resuelva Y no rechace. El fake modela los dos desenlaces reales y
 * los dos afirman sobre `setLoading`, que es un espía y no un booleano prefabricado. Sacar el
 * `finally` rojea los dos; moverlo adentro del `try` rojea el del error, que es el caso que el
 * usuario ve peor: pantalla cargando encima de un mensaje que nadie llega a leer.
 *
 * Se testea la FUNCIÓN y no la pantalla: vitest corre sin jsdom, los `useEffect` no se ejecutan y
 * un render a string mostraría el skeleton inicial con el fix y sin él.
 */

const fetchHorasPorCliente = vi.fn()
vi.mock("@/services/horasCliente", () => ({
  fetchHorasPorCliente: (...a: unknown[]) => fetchHorasPorCliente(...a),
}))

const { cargarHorasCliente, ERROR_CARGA } = await import(
  "@/components/features/horasCliente/cargarHorasCliente"
)

function espias() {
  return { setDatos: vi.fn(), setLoading: vi.fn(), setError: vi.fn() }
}
const DATOS = { mes: 8, anio: 2026, kpis: {}, clientes: [] }

afterEach(() => fetchHorasPorCliente.mockReset())

describe("cargarHorasCliente apaga el loading", () => {
  it("con respuesta exitosa", async () => {
    fetchHorasPorCliente.mockResolvedValue(DATOS)
    const e = espias()

    await cargarHorasCliente({ mes: 8, anio: 2026 }, e)

    expect(e.setDatos).toHaveBeenCalledWith(DATOS)
    expect(e.setLoading).toHaveBeenLastCalledWith(false)
    expect(e.setError).not.toHaveBeenCalledWith(ERROR_CARGA)
  })

  it("con error de red", async () => {
    fetchHorasPorCliente.mockRejectedValue(new Error("network"))
    const e = espias()

    await cargarHorasCliente({ mes: 8, anio: 2026 }, e)

    expect(e.setError).toHaveBeenCalledWith(ERROR_CARGA)
    expect(e.setLoading).toHaveBeenLastCalledWith(false)
  })

  it("el filtro de mes viaja al service y no se pierde", async () => {
    // Si no llegara, el listado y el export dejarían de coincidir (invariante 1 del bloque B).
    fetchHorasPorCliente.mockResolvedValue(DATOS)

    await cargarHorasCliente({ mes: 3, anio: 2025 }, espias())

    expect(fetchHorasPorCliente).toHaveBeenCalledWith({ mes: 3, anio: 2025 })
  })
})
