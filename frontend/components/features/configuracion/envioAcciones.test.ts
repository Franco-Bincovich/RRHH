import { afterEach, describe, expect, it, vi } from "vitest"

/**
 * Lo que VIAJA al backend cuando RRHH aprieta "Sí, enviar".
 *
 * Es la parte irreversible del módulo de mails: el body de este POST decide a quién le llega un
 * mail a nombre de la empresa. Mandarle a alguien de más no se deshace.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. EL CATÁLOGO TIENE TRES EMPLEADOS Y SE ELIGEN DOS. Es la condición sin la cual el test más
 *    importante no prueba nada: con un solo empleado en el fake, una implementación que ignore
 *    la selección y mande la lista entera daría EXACTAMENTE el mismo body y pasaría en verde.
 *    Con tres y dos elegidos, "manda a todos" produce tres ids y rojea. Y se afirma sobre el
 *    body COMPLETO (`toEqual`, no `toContain`): un tercer id de más tiene que romper.
 * 2. `destinatarios` RECIBE LAS DOS COSAS —catálogo y selección— justamente para que "manda a
 *    todos" sea un desenlace expresable. Si la función recibiera solo los ids ya elegidos, no
 *    habría nadie de más a quien mandarle y el test sería vacuo por diseño.
 * 3. `enviarPlantilla` es un espía de verdad (`vi.fn`), no un stub que devuelve una constante:
 *    se afirma sobre lo que RECIBIÓ, no sobre lo que este archivo le pasó. Y el caso de cero
 *    seleccionados afirma que NO fue llamado — un `expect(body).toEqual([])` sobre una llamada
 *    que igual ocurrió daría verde con el pedido saliendo hacia el backend.
 * 4. El fake modela los DOS desenlaces de la red (resuelve y rechaza). Con solo el camino feliz,
 *    un `catch` borrado dejaría la promesa rechazada suelta y el modal colgado en "Enviando…".
 */

const enviarPlantilla = vi.fn()
vi.mock("@/services/plantillas", () => ({
  enviarPlantilla: (...a: unknown[]) => enviarPlantilla(...a),
}))

const { destinatarios, enviarAhora, ERROR_ENVIO } =
  await import("@/components/features/configuracion/envioAcciones")

/** TRES, no uno: ver el punto 1 del encabezado. */
const EMPLEADOS = [
  { id: "e1", nombre: "Ana", apellido: "Uno", email_corporativo: "ana@k.com" },
  { id: "e2", nombre: "Beto", apellido: "Dos", email_corporativo: "beto@k.com" },
  { id: "e3", nombre: "Cari", apellido: "Tres", email_corporativo: "cari@k.com" },
]
const OK = { enviados: 2, omitidos: 0, fallidos: [], parcial: false, sin_procesar: 0, segundos: 3 }

afterEach(() => enviarPlantilla.mockReset())

describe("manda a los seleccionados, no a todos", () => {
  it("🔴 con 3 empleados y 2 elegidos, viajan esos 2 ids y la clave", async () => {
    enviarPlantilla.mockResolvedValue(OK)

    await enviarAhora("bienvenida", EMPLEADOS, new Set(["e1", "e3"]))

    expect(enviarPlantilla).toHaveBeenCalledTimes(1)
    // Body completo: si la implementación mandara los tres, este toEqual rojea.
    expect(enviarPlantilla).toHaveBeenCalledWith("bienvenida", ["e1", "e3"])
  })

  it("elegir uno solo manda uno solo (el caso de arriba no está pasando por otra vía)", async () => {
    enviarPlantilla.mockResolvedValue(OK)

    await enviarAhora("aviso", EMPLEADOS, new Set(["e2"]))

    expect(enviarPlantilla).toHaveBeenCalledWith("aviso", ["e2"])
  })

  it("un id seleccionado que ya no está en el catálogo NO viaja", async () => {
    // Pasa de verdad: se elige a alguien, cambia el filtro de búsqueda o se da de baja, y el id
    // queda en la Set. Mandarle un mail a un empleado que la pantalla ya no muestra es el tipo
    // de sorpresa que no se puede deshacer.
    enviarPlantilla.mockResolvedValue(OK)

    await enviarAhora("aviso", EMPLEADOS, new Set(["e1", "fantasma"]))

    expect(enviarPlantilla).toHaveBeenCalledWith("aviso", ["e1"])
  })

  it("`destinatarios` respeta el orden del catálogo, no el de la selección", () => {
    expect(destinatarios(EMPLEADOS, new Set(["e3", "e1"]))).toEqual(["e1", "e3"])
  })
})

describe("con cero seleccionados no se puede enviar", () => {
  it("🔴 no se llama al backend", async () => {
    const r = await enviarAhora("bienvenida", EMPLEADOS, new Set())

    // Si se llamara con [], el backend gastaría uno de los 20 pedidos por hora del rate limit
    // y devolvería un 200 que la pantalla mostraría como "salieron todos" (0 enviados).
    expect(enviarPlantilla).not.toHaveBeenCalled()
    expect(r).toEqual({ ok: false, error: "Elegí al menos una persona." })
  })

  it("una selección que no matchea a nadie del catálogo tampoco llama", async () => {
    await enviarAhora("bienvenida", EMPLEADOS, new Set(["fantasma"]))

    expect(enviarPlantilla).not.toHaveBeenCalled()
  })
})

describe("el error de red no queda suelto", () => {
  it("nunca rechaza: devuelve el mensaje del backend, que es accionable", async () => {
    enviarPlantilla.mockRejectedValue(new Error("Conectá una cuenta de Gmail en Configuración"))

    const r = await enviarAhora("bienvenida", EMPLEADOS, new Set(["e1"]))

    expect(r).toEqual({ ok: false, error: "Conectá una cuenta de Gmail en Configuración" })
  })

  it("y cae a un texto propio cuando el error no trae mensaje", async () => {
    enviarPlantilla.mockRejectedValue(new Error(""))

    const r = await enviarAhora("bienvenida", EMPLEADOS, new Set(["e1"]))

    expect(r).toEqual({ ok: false, error: ERROR_ENVIO })
  })

  it("el resultado exitoso se devuelve tal cual vino, sin colapsarlo a un booleano", async () => {
    // Los cinco números son el punto: ver EnvioResultado.test.tsx.
    const parcial = { ...OK, enviados: 1, parcial: true, sin_procesar: 1 }
    enviarPlantilla.mockResolvedValue(parcial)

    expect(await enviarAhora("bienvenida", EMPLEADOS, new Set(["e1", "e2"])))
      .toEqual({ ok: true, res: parcial })
  })
})
