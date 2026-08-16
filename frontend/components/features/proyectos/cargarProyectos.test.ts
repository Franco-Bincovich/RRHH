import { afterEach, describe, expect, it, vi } from "vitest"

/**
 * El listado de proyectos quedó en skeleton para siempre —con el endpoint respondiendo 200—
 * porque el `finally { setLoading(false) }` se perdió al dividir la página (commit e3df1f9).
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * Que `fetchProyectos` NO resuelva y NO rechace. El fake modela los tres desenlaces reales
 * —resuelve con items, resuelve vacío, rechaza— y cada uno afirma sobre `setLoading`, que es
 * un espía de verdad y no un booleano prefabricado. Sacar el `finally` rojea los tres; moverlo
 * adentro del `try` rojea el del error, que es exactamente el caso que el usuario ve peor
 * (pantalla cargando encima de un error que ya se escribió y nadie llega a leer).
 *
 * Se testea la FUNCIÓN y no el componente a propósito: vitest corre sin jsdom, los efectos no
 * se ejecutan, y un render a string mostraría el skeleton inicial tanto con el fix como sin él.
 */

const fetchProyectos = vi.fn()
vi.mock("@/services/proyectos", () => ({ fetchProyectos: (...a: unknown[]) => fetchProyectos(...a) }))

const { cargarProyectos, ERROR_CARGA } = await import("@/components/features/proyectos/cargarProyectos")

function espias() {
  return { setProyectos: vi.fn(), setLoading: vi.fn(), setError: vi.fn(), setTotal: vi.fn() }
}
const PROYECTO = { id: "p1", nombre: "Uno" }

afterEach(() => fetchProyectos.mockReset())

describe("cargarProyectos apaga el loading", () => {
  it("con respuesta exitosa", async () => {
    fetchProyectos.mockResolvedValue({ items: [PROYECTO], total: 1 })
    const e = espias()

    await cargarProyectos({}, e)

    expect(e.setProyectos).toHaveBeenCalledWith([PROYECTO])
    expect(e.setLoading).toHaveBeenLastCalledWith(false)
    expect(e.setError).not.toHaveBeenCalledWith(ERROR_CARGA)
  })

  it("con error de red", async () => {
    fetchProyectos.mockRejectedValue(new Error("network"))
    const e = espias()

    await cargarProyectos({}, e)

    expect(e.setLoading).toHaveBeenLastCalledWith(false)
  })

  it("con lista vacía", async () => {
    fetchProyectos.mockResolvedValue({ items: [], total: 0 })
    const e = espias()

    await cargarProyectos({}, e)

    expect(e.setProyectos).toHaveBeenCalledWith([])
    expect(e.setLoading).toHaveBeenLastCalledWith(false)
  })

  it("con un 200 sin items (no revienta la grilla ni deja cargando)", async () => {
    fetchProyectos.mockResolvedValue({ total: 0 })
    const e = espias()

    await cargarProyectos({}, e)

    expect(e.setProyectos).toHaveBeenCalledWith([])
    expect(e.setLoading).toHaveBeenLastCalledWith(false)
  })

  it("prende antes de pedir y apaga después: el orden importa", async () => {
    fetchProyectos.mockResolvedValue({ items: [], total: 0 })
    const e = espias()

    await cargarProyectos({}, e)

    // Si estas dos llamadas se invirtieran, la pantalla arrancaría a cargar y no pararía.
    expect(e.setLoading.mock.calls).toEqual([[true], [false]])
  })

  it("nunca lanza: el error se convierte en mensaje visible, no en promesa rechazada", async () => {
    fetchProyectos.mockRejectedValue(new Error("network"))
    const e = espias()

    await expect(cargarProyectos({}, e)).resolves.toBeUndefined()
    expect(e.setError).toHaveBeenCalledWith(ERROR_CARGA)
  })

  it("limpia el error anterior al reintentar, para que un reintento exitoso no lo deje pegado", async () => {
    fetchProyectos.mockResolvedValue({ items: [PROYECTO], total: 1 })
    const e = espias()

    await cargarProyectos({}, e)

    expect(e.setError).toHaveBeenCalledWith(null)
  })

  it("pasa los filtros tal cual al service, junto con la página", async () => {
    fetchProyectos.mockResolvedValue({ items: [], total: 0 })

    await cargarProyectos({ estado: "activo", areaId: "a1" }, espias(), 3, 20)

    // Los filtros viajan SIN tocar y la página va aparte: el service es el que la traduce a
    // params, para que `queryProyectos` —que comparte con el export— no la vea.
    expect(fetchProyectos).toHaveBeenCalledWith({ estado: "activo", areaId: "a1" }, 3, 20)
  })

  it("el total sale de la respuesta, no del largo de la página", async () => {
    // Es el molde: con paginación, un total derivado de `items` diría 2 sobre 137.
    fetchProyectos.mockResolvedValue({ items: [{}, {}], total: 137 })
    const e = espias()

    await cargarProyectos({}, e, 1, 2)

    expect(e.setTotal).toHaveBeenCalledWith(137)
  })
})
