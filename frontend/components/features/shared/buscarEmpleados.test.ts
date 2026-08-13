import { afterEach, describe, expect, it, vi } from "vitest"

import { MAX_PAGE_SIZE } from "@/services/api"

/**
 * La búsqueda del selector de empleados, contra un padrón de 400.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * **1. 🔴 EL PADRÓN TIENE QUE TENER MÁS DE 100. Es LA condición del archivo.** Con 20 empleados
 * el truncamiento no se manifiesta: pedir una página de 100 sin filtro los trae a todos, y el
 * test del empleado 350 pasaría con el bug intacto. Es exactamente la trampa que dejó el defecto
 * vivo — hay un test abajo que verifica esta propiedad del fake ANTES de confiar en los demás.
 *
 * **2. 🔴 EL FAKE FILTRA Y PAGINA COMO EL BACKEND**, no devuelve una lista fija. Si ignorara
 * `search`, mandar el término o no mandarlo daría el mismo resultado y la mutación "volvé a
 * pedir una sola página de 100" quedaría en verde. Acá `search` hace `includes` sobre nombre Y
 * apellido —las dos columnas del `or` de `empleado_repo.py:56-58`— y después corta por página.
 *
 * **3. 🔴 EL FAKE RECHAZA `pageSize > 100` CON 422**, como el `Query(20, ge=1, le=100)` del
 * router. Sin eso, un fake permisivo aceptaría la vieja "solución" de subir el número, que es
 * justo la que ya llegó a producción y dejó dos modales mostrando "no hay empleados".
 *
 * **4. 🔴 ERROR Y LISTA VACÍA SE AFIRMAN UNO CONTRA EL OTRO.** Es la invariante que rescató el
 * bug anterior y no se puede perder al cambiar de estrategia de carga: un backend caído tiene
 * que verse como un error, no como "no hay nadie con ese nombre".
 *
 * Se prueba la FUNCIÓN y no el componente porque vitest corre sin jsdom: un `useEffect` no se
 * ejecuta y un render a string mostraría el mismo markup con el bug y sin él. Molde:
 * `cargarEmpleados.test.ts`.
 */

const fetchEmpleados = vi.fn()
vi.mock("@/services/empleados", () => ({ fetchEmpleados: (...a: unknown[]) => fetchEmpleados(...a) }))

const { buscarEmpleados, RESULTADOS_VISIBLES } =
  await import("@/components/features/shared/buscarEmpleados")

// 400 colaboradores: el número del diagnóstico de escala, y CUATRO veces el tope del endpoint.
const PADRON = Array.from({ length: 400 }, (_, i) => ({
  id: `e${i + 1}`,
  nombre: `Nombre${i + 1}`,
  apellido: `Apellido${i + 1}`,
  empresa_id: "emp1",
}))

// El que está en la posición 350: fuera de los primeros 100 por definición.
const LEJANO = PADRON[349]

interface Pedido {
  page: number
  pageSize: number
  search?: string
  estado?: string
  empresaId?: string
}

/** Filtra por `search` sobre nombre y apellido, pagina, y rechaza como el `le=100` del router. */
function backendFalso(opts: Pedido) {
  if (opts.pageSize > MAX_PAGE_SIZE) throw new Error("422 Unprocessable Entity")
  const q = (opts.search ?? "").toLowerCase()
  const filtrados = q
    ? PADRON.filter((e) =>
        e.nombre.toLowerCase().includes(q) || e.apellido.toLowerCase().includes(q))
    : PADRON
  const desde = (opts.page - 1) * opts.pageSize
  return {
    items: filtrados.slice(desde, desde + opts.pageSize),
    total: filtrados.length,
    page: opts.page,
    page_size: opts.pageSize,
    total_pages: Math.ceil(filtrados.length / opts.pageSize),
  }
}

function espias() {
  return { setEmpleados: vi.fn(), setCargando: vi.fn(), setError: vi.fn(), setTotal: vi.fn() }
}

/** Los empleados con los que quedó la pantalla. */
function resultado(e: ReturnType<typeof espias>) {
  return e.setEmpleados.mock.calls.at(-1)![0] as { id: string }[]
}

afterEach(() => fetchEmpleados.mockReset())

describe("el fake puede desmentir algo", () => {
  it("🔴 el padrón supera el tope del endpoint (si no, NINGÚN test de acá puede fallar)", () => {
    expect(PADRON.length).toBeGreaterThan(MAX_PAGE_SIZE)
    // Y el que se busca está fuera de la primera página, que es lo que hace al caso un caso.
    expect(PADRON.indexOf(LEJANO)).toBeGreaterThan(MAX_PAGE_SIZE)
  })

  it("🔴 el fake filtra de verdad: sin `search` devuelve la página, con `search` devuelve el que coincide", () => {
    expect(backendFalso({ page: 1, pageSize: 100 }).items).toHaveLength(100)
    expect(backendFalso({ page: 1, pageSize: 20, search: "Nombre350" }).items).toEqual([LEJANO])
  })

  it("🔴 y rechaza pedir más de 100, como el router", () => {
    expect(() => backendFalso({ page: 1, pageSize: 200 })).toThrow("422")
  })
})

describe("un empleado fuera de los primeros 100", () => {
  it("🔴 buscar al que está en la posición 350 lo encuentra", async () => {
    fetchEmpleados.mockImplementation((o: Pedido) => Promise.resolve(backendFalso(o)))
    const e = espias()

    await buscarEmpleados({ termino: "Nombre350" }, e)

    expect(resultado(e).map((x) => x.id)).toContain(LEJANO.id)
    expect(e.setError).toHaveBeenLastCalledWith(false)
  })

  it("🔴 el término viaja al BACKEND, no se filtra en memoria", async () => {
    // Es la aserción que distingue los dos caminos posibles: si el filtro se hiciera del lado del
    // cliente, el pedido saldría sin `search` y el de arriba pasaría igual solo si además se
    // pidieran las 400 filas — que es lo que el tope de 100 impide.
    fetchEmpleados.mockImplementation((o: Pedido) => Promise.resolve(backendFalso(o)))

    await buscarEmpleados({ termino: "  Nombre350  ", empresaId: "emp1" }, espias())

    expect(fetchEmpleados).toHaveBeenCalledWith(
      expect.objectContaining({ search: "Nombre350", empresaId: "emp1", estado: "activo" }))
  })

  it("y nunca pide más de lo que el endpoint acepta", async () => {
    fetchEmpleados.mockImplementation((o: Pedido) => Promise.resolve(backendFalso(o)))

    await buscarEmpleados({ termino: "" }, espias())

    expect(RESULTADOS_VISIBLES).toBeLessThanOrEqual(MAX_PAGE_SIZE)
    expect(fetchEmpleados).toHaveBeenCalledWith(
      expect.objectContaining({ pageSize: RESULTADOS_VISIBLES }))
  })
})

describe("los tres desenlaces siguen siendo tres", () => {
  it("🔴 buscar algo que no existe NO es un error: lista vacía y error en false", async () => {
    fetchEmpleados.mockImplementation((o: Pedido) => Promise.resolve(backendFalso(o)))
    const e = espias()

    await buscarEmpleados({ termino: "Zzzznadie" }, e)

    expect(resultado(e)).toEqual([])
    expect(e.setError).toHaveBeenLastCalledWith(false)
  })

  it("🔴 si el backend falla, marca ERROR — no una lista vacía", async () => {
    fetchEmpleados.mockRejectedValue(new Error("500"))
    const e = espias()

    await buscarEmpleados({ termino: "Nombre350" }, e)

    expect(e.setError).toHaveBeenLastCalledWith(true)
    expect(resultado(e)).toEqual([])
  })

  it("y el loading se apaga en los dos caminos", async () => {
    fetchEmpleados.mockRejectedValue(new Error("500"))
    const e = espias()

    await buscarEmpleados({ termino: "x" }, e)

    expect(e.setCargando.mock.calls).toEqual([[true], [false]])
  })
})

describe("el total que la pantalla necesita para avisar que está mostrando una parte", () => {
  it("🔴 sin término, informa las 400 aunque solo traiga 20", async () => {
    fetchEmpleados.mockImplementation((o: Pedido) => Promise.resolve(backendFalso(o)))
    const e = espias()

    await buscarEmpleados({ termino: "" }, e)

    expect(resultado(e)).toHaveLength(RESULTADOS_VISIBLES)
    expect(e.setTotal).toHaveBeenLastCalledWith(400)
  })

  it("y en el error el total vuelve a cero, para no dejar pegado un número de la búsqueda anterior", async () => {
    fetchEmpleados.mockRejectedValue(new Error("500"))
    const e = espias()

    await buscarEmpleados({ termino: "x" }, e)

    expect(e.setTotal).toHaveBeenLastCalledWith(0)
  })
})
