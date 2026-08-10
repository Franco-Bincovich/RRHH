import { afterEach, describe, expect, it, vi } from "vitest"

/**
 * La carga del catálogo apaga el loading SIEMPRE.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * Que `fetchClientes` no resuelva Y no rechace. El fake modela los TRES desenlaces reales
 * —resuelve con items, resuelve sin `items`, rechaza— y cada uno afirma sobre `setLoading`, que
 * es un espía de verdad y no un booleano prefabricado. Sacar el `finally` rojea los tres; moverlo
 * adentro del `try` rojea solo el del error, que es justo el caso que el usuario ve peor:
 * pantalla cargando encima de un mensaje de error que nadie llega a leer.
 *
 * Se testea la FUNCIÓN y no la pantalla a propósito: vitest corre SIN jsdom, así que los
 * `useEffect` NO se ejecutan y un render a string mostraría el skeleton inicial tanto con el fix
 * como sin él. Es el caso #4 de "un test solo prueba lo que el fake puede desmentir".
 */

const fetchClientes = vi.fn()
vi.mock("@/services/clientes", () => ({
  fetchClientes: (...a: unknown[]) => fetchClientes(...a),
}))

const { cargarClientes, ERROR_CARGA } = await import(
  "@/components/features/clientes/cargarClientes"
)

function espias() {
  return { setClientes: vi.fn(), setLoading: vi.fn(), setError: vi.fn() }
}
const CLIENTE = { id: "c1", nombre: "Acme", activo: true }

afterEach(() => fetchClientes.mockReset())

describe("cargarClientes apaga el loading", () => {
  it("con respuesta exitosa", async () => {
    fetchClientes.mockResolvedValue({ items: [CLIENTE], total: 1 })
    const e = espias()

    await cargarClientes({}, e)

    expect(e.setClientes).toHaveBeenCalledWith([CLIENTE])
    expect(e.setLoading).toHaveBeenLastCalledWith(false)
    expect(e.setError).not.toHaveBeenCalledWith(ERROR_CARGA)
  })

  it("con error de red", async () => {
    fetchClientes.mockRejectedValue(new Error("network"))
    const e = espias()

    await cargarClientes({}, e)

    expect(e.setError).toHaveBeenCalledWith(ERROR_CARGA)
    expect(e.setLoading).toHaveBeenLastCalledWith(false)
  })

  it("con un 200 sin items", async () => {
    // Sin el `?? []` la tabla revienta al leer .length y el síntoma es una pantalla en blanco
    // que tampoco dice qué pasó.
    fetchClientes.mockResolvedValue({})
    const e = espias()

    await cargarClientes({}, e)

    expect(e.setClientes).toHaveBeenCalledWith([])
    expect(e.setLoading).toHaveBeenLastCalledWith(false)
  })

  it("el filtro viaja al service, no se pierde en el camino", async () => {
    // Si el filtro no llegara, el listado y el export dejarían de coincidir — que es la
    // invariante del bloque B (el archivo no puede traer filas que la pantalla no muestre).
    fetchClientes.mockResolvedValue({ items: [], total: 0 })

    await cargarClientes({ incluirInactivos: true }, espias())

    expect(fetchClientes).toHaveBeenCalledWith({ incluirInactivos: true })
  })
})
