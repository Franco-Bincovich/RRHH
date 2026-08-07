import { afterEach, describe, expect, it, vi } from "vitest"

/**
 * Los TRES desenlaces de cargar el historial: cargando · error · lista.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. 🔴 EL FAKE PUEDE RECHAZAR, no solo devolver `{items: []}`. Es la condición sin la cual el
 *    archivo no prueba nada: con un fake que siempre resuelve, la rama del `catch` no se ejecuta
 *    jamás y borrar el `setError(true)` quedaría en verde. Y "error" y "todavía no se envió
 *    ningún mail" volverían a ser el mismo estado — que es exactamente el bug que este repo ya
 *    se comió con "no hay empleados" sobre una base llena.
 * 2. Los dos casos se afirman UNO CONTRA EL OTRO: el rechazo exige `setError(true)` y la lista
 *    vacía exige `setError(false)`. Con solo el primero, un `setError(true)` incondicional
 *    pasaría y la pantalla diría "no se pudo cargar" con el historial sano.
 * 3. Los setters son espías (`vi.fn`): se afirma sobre lo que RECIBIERON y sobre el ORDEN.
 *    `setCargando.mock.calls` igual a `[[true], [false]]` rojea si alguien mueve el apagado
 *    adentro del `try`, que dejaría el spinner encima del mensaje de error.
 * 4. Se prueba la FUNCIÓN y no el hook ni el componente: vitest corre sin jsdom, los `useEffect`
 *    no se ejecutan y un render a string daría el mismo markup con el bug y sin él. Por eso la
 *    carga se extrajo del hook (molde: `cargarProyectos`, `cargarEmpleados`).
 */

const fetchHistorialMails = vi.fn()
vi.mock("@/services/mails", () => ({
  fetchHistorialMails: (...a: unknown[]) => fetchHistorialMails(...a),
}))

const { cargarHistorialMails } =
  await import("@/components/features/comunicacion/cargarHistorialMails")

function espias() {
  return { setItems: vi.fn(), setLimite: vi.fn(), setCargando: vi.fn(), setError: vi.fn() }
}

const MAIL = {
  id: "m1", plantilla_clave: "bienvenida", destinatario: "ana@k.com",
  asunto_render: "Hola", estado: "enviado", error: null,
  created_at: "2026-08-07T13:00:00+00:00",
}

afterEach(() => fetchHistorialMails.mockReset())

describe("error y historial vacío son estados DISTINTOS", () => {
  it("🔴 si la consulta falla, marca error", async () => {
    fetchHistorialMails.mockRejectedValue(new Error("network"))
    const e = espias()

    await cargarHistorialMails({}, e)

    expect(e.setError).toHaveBeenLastCalledWith(true)
    expect(e.setItems).toHaveBeenLastCalledWith([])
  })

  it("🔴 si no hay mails todavía, NO marca error", async () => {
    fetchHistorialMails.mockResolvedValue({ items: [], limite: 100 })
    const e = espias()

    await cargarHistorialMails({}, e)

    expect(e.setError).toHaveBeenLastCalledWith(false)
    expect(e.setItems).toHaveBeenLastCalledWith([])
  })

  it("con datos, pasa los items y el límite", async () => {
    fetchHistorialMails.mockResolvedValue({ items: [MAIL], limite: 100 })
    const e = espias()

    await cargarHistorialMails({}, e)

    expect(e.setItems).toHaveBeenCalledWith([MAIL])
    expect(e.setLimite).toHaveBeenCalledWith(100)
    expect(e.setError).toHaveBeenLastCalledWith(false)
  })

  it("limpia el error anterior al reintentar", async () => {
    fetchHistorialMails.mockResolvedValue({ items: [MAIL], limite: 100 })
    const e = espias()

    await cargarHistorialMails({}, e)

    expect(e.setError.mock.calls).toEqual([[false]])
  })
})

describe("el loading se apaga SIEMPRE", () => {
  it("🔴 también en el camino de error", async () => {
    fetchHistorialMails.mockRejectedValue(new Error("network"))
    const e = espias()

    await cargarHistorialMails({}, e)

    expect(e.setCargando.mock.calls).toEqual([[true], [false]])
  })

  it("y en el camino feliz, en ese orden", async () => {
    fetchHistorialMails.mockResolvedValue({ items: [], limite: 100 })
    const e = espias()

    await cargarHistorialMails({}, e)

    expect(e.setCargando.mock.calls).toEqual([[true], [false]])
  })

  it("nunca rechaza: el error se convierte en estado", async () => {
    fetchHistorialMails.mockRejectedValue(new Error("network"))

    await expect(cargarHistorialMails({}, espias())).resolves.toBeUndefined()
  })

  it("un 200 sin `items` no rompe la tabla ni deja cargando", async () => {
    fetchHistorialMails.mockResolvedValue({ limite: 100 })
    const e = espias()

    await cargarHistorialMails({}, e)

    expect(e.setItems).toHaveBeenCalledWith([])
    expect(e.setCargando).toHaveBeenLastCalledWith(false)
  })
})

describe("los filtros viajan tal cual al service", () => {
  it("estado y rango de fechas llegan con los nombres del contrato", async () => {
    fetchHistorialMails.mockResolvedValue({ items: [], limite: 100 })

    await cargarHistorialMails(
      { estado: "fallido", fecha_desde: "2026-08-01", fecha_hasta: "2026-08-07" }, espias())

    expect(fetchHistorialMails).toHaveBeenCalledWith({
      estado: "fallido", fecha_desde: "2026-08-01", fecha_hasta: "2026-08-07",
    })
  })

  it("sin filtros, manda el objeto vacío (no inventa uno)", async () => {
    fetchHistorialMails.mockResolvedValue({ items: [], limite: 100 })

    await cargarHistorialMails({}, espias())

    expect(fetchHistorialMails).toHaveBeenCalledWith({})
  })
})
