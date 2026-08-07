import { afterEach, describe, expect, it, vi } from "vitest"

/**
 * Los TRES desenlaces de cargar un selector de empleados: cargando · error · lista.
 *
 * Es el test que faltaba cuando `page_size=200` llegó a producción. El backend respondía **422 en
 * el 100% de los requests** y dos modales mostraban "no hay empleados" con 31 activos en la base,
 * con la suite entera en verde: ningún test podía notarlo porque el único `.catch` que existía
 * hacía `setEmpleados([])` y descartaba el error, así que **"falló" y "no hay nadie" eran el
 * mismo estado** y ningún fake podía distinguirlos.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. EL FAKE PUEDE RECHAZAR, no solo devolver `[]`. Es la condición sin la cual este archivo no
 *    prueba nada: con un fake que siempre resuelve, el camino del `catch` no se ejecuta jamás y
 *    borrar el `setError(true)` dejaría todo en verde. Los dos casos —rechazo y lista vacía— se
 *    afirman UNO CONTRA EL OTRO (`setError` con `true` vs con `false`), que es exactamente la
 *    distinción que la pantalla necesita y que antes no existía.
 * 2. Los setters son espías de verdad (`vi.fn`), así que se afirma sobre lo que RECIBIERON y
 *    sobre el ORDEN. `setCargando.mock.calls` igual a `[[true], [false]]` rojea si alguien mueve
 *    el apagado adentro del `try`: ahí el camino de error dejaría la pantalla cargando encima
 *    del mensaje de error, que es la regresión que ya se llevó puesta la pantalla de proyectos.
 * 3. Se prueba la FUNCIÓN, no el hook ni el componente, a propósito: vitest corre sin jsdom, los
 *    `useEffect` no se ejecutan y un render a string mostraría el mismo markup con el bug y sin
 *    él. Por eso la carga se extrajo del hook (molde: `cargarProyectos`).
 *
 * ⚠️ LO QUE QUEDA SIN RED, explícito: que los hooks (`useDestinatarios`, `useCandidatosProyecto`)
 * CABLEEN bien estos setters a su estado, y que pasen `MAX_PAGE_SIZE`. Lo primero no se puede
 * testear en esta suite; lo segundo lo cubre el barrido `services/pageSize.test.ts`.
 */

const fetchEmpleados = vi.fn()
vi.mock("@/services/empleados", () => ({ fetchEmpleados: (...a: unknown[]) => fetchEmpleados(...a) }))

const { cargarEmpleados } = await import("@/components/features/shared/cargarEmpleados")

function espias() {
  return { setEmpleados: vi.fn(), setCargando: vi.fn(), setError: vi.fn() }
}
const FILTROS = { page: 1, pageSize: 100, estado: "activo" }
const EMPLEADO = { id: "e1", nombre: "Ana", apellido: "Uno" }

afterEach(() => fetchEmpleados.mockReset())

describe("error y lista vacía son estados DISTINTOS", () => {
  it("🔴 si la consulta falla, marca error (no lo disfraza de lista vacía)", async () => {
    fetchEmpleados.mockRejectedValue(new Error("422"))
    const e = espias()

    await cargarEmpleados(FILTROS, e)

    expect(e.setError).toHaveBeenLastCalledWith(true)
    expect(e.setEmpleados).toHaveBeenLastCalledWith([])
  })

  it("🔴 si la consulta va bien pero no hay nadie, NO marca error", async () => {
    // Sin este caso, el de arriba pasaría con un `setError(true)` incondicional, que es igual de
    // malo: diría "no se pudieron cargar" sobre una empresa que legítimamente no tiene activos.
    fetchEmpleados.mockResolvedValue({ items: [], total: 0 })
    const e = espias()

    await cargarEmpleados(FILTROS, e)

    expect(e.setError).toHaveBeenLastCalledWith(false)
    expect(e.setEmpleados).toHaveBeenLastCalledWith([])
  })

  it("con datos, tampoco marca error y pasa los items", async () => {
    fetchEmpleados.mockResolvedValue({ items: [EMPLEADO], total: 1 })
    const e = espias()

    await cargarEmpleados(FILTROS, e)

    expect(e.setEmpleados).toHaveBeenCalledWith([EMPLEADO])
    expect(e.setError).toHaveBeenLastCalledWith(false)
  })

  it("limpia el error anterior al reintentar, para que un reintento exitoso no lo deje pegado", async () => {
    fetchEmpleados.mockResolvedValue({ items: [EMPLEADO], total: 1 })
    const e = espias()

    await cargarEmpleados(FILTROS, e)

    expect(e.setError.mock.calls).toEqual([[false]])
  })
})

describe("el loading se apaga SIEMPRE", () => {
  it("🔴 también en el camino de error (si no, el mensaje queda tapado por el spinner)", async () => {
    fetchEmpleados.mockRejectedValue(new Error("network"))
    const e = espias()

    await cargarEmpleados(FILTROS, e)

    expect(e.setCargando.mock.calls).toEqual([[true], [false]])
  })

  it("y en el camino feliz, en ese orden", async () => {
    fetchEmpleados.mockResolvedValue({ items: [], total: 0 })
    const e = espias()

    await cargarEmpleados(FILTROS, e)

    // Invertidas, la pantalla arrancaría a cargar y no pararía nunca.
    expect(e.setCargando.mock.calls).toEqual([[true], [false]])
  })
})

describe("no propaga y no revienta con respuestas raras", () => {
  it("nunca rechaza: el error se convierte en estado, no en promesa suelta", async () => {
    fetchEmpleados.mockRejectedValue(new Error("network"))

    await expect(cargarEmpleados(FILTROS, espias())).resolves.toBeUndefined()
  })

  it("un 200 sin `items` no rompe la lista ni deja cargando", async () => {
    fetchEmpleados.mockResolvedValue({ total: 0 })
    const e = espias()

    await cargarEmpleados(FILTROS, e)

    expect(e.setEmpleados).toHaveBeenCalledWith([])
    expect(e.setCargando).toHaveBeenLastCalledWith(false)
    expect(e.setError).toHaveBeenLastCalledWith(false)
  })
})

describe("los filtros viajan tal cual al service", () => {
  it("incluido el pageSize, que es el que rompió esto", async () => {
    fetchEmpleados.mockResolvedValue({ items: [], total: 0 })

    await cargarEmpleados({ page: 1, pageSize: 100, estado: "activo", empresaId: "todas" }, espias())

    expect(fetchEmpleados).toHaveBeenCalledWith({
      page: 1, pageSize: 100, estado: "activo", empresaId: "todas",
    })
  })
})
