import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { beforeEach, describe, expect, it, vi } from "vitest"

const { activarEmpleado, toastError, toastSuccess } = vi.hoisted(() => ({
  activarEmpleado: vi.fn(), toastError: vi.fn(), toastSuccess: vi.fn(),
}))
vi.mock("@/services/empleados", () => ({ activarEmpleado }))
vi.mock("sonner", () => ({ toast: { error: toastError, success: toastSuccess } }))

import { ApiError } from "@/services/api"

import { confirmarIngreso } from "./useActivarEmpleado"

/**
 * (b) y (c) del ciclo de vida: confirmar un ingreso desde la fila de /proximos-ingresos.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * · El fake de `activarEmpleado` distingue los TRES desenlaces que importan (OK · `ApiError` con
 *   mensaje · error pelado), y cada uno tiene su aserción. Con un fake que siempre resuelva, (c)
 *   —el caso que de verdad se encuentra operando— no podría aparecer nunca.
 * · (c) compara contra EL MENSAJE COMPLETO del backend, no contra un `toContain("2026")`: la
 *   forma en que esto se rompe es que alguien lo reemplace por un genérico, y un genérico pasa
 *   cualquier aserción parcial que no mire el string entero.
 * · El caso "error pelado" es la contracara: sin él, un `toast.error(e.message)` sin el `instanceof`
 *   pasaría (c) igual y le mostraría a Capital Humano un "Failed to fetch".
 *
 * 🚩 LO QUE NO CUBRE, dicho explícito: el CLICK. vitest corre sin jsdom, así que no hay forma de
 * apretar el botón de la fila. Lo que sí se verifica es la función que ese botón invoca y —abajo—
 * que la página le pase el `recargar` correcto, que son las dos mitades de "la fila desaparece".
 */

const ANA = { id: "e-1", nombre: "Ana", apellido: "Pérez" }

beforeEach(() => {
  activarEmpleado.mockReset().mockResolvedValue(undefined)
  toastError.mockReset()
  toastSuccess.mockReset()
})

describe("(b) confirmar un ingreso saca la fila de próximos ingresos", () => {
  it("llama al endpoint del ACTO con el id de esa persona", async () => {
    // No es un PUT con `estado: "activo"`: ese camino se saltearía las dos guardas del backend.
    await confirmarIngreso(ANA, () => {})
    expect(activarEmpleado).toHaveBeenCalledWith("e-1")
  })

  it("y recién cuando salió bien avisa al listado para que se recargue", async () => {
    const recargar = vi.fn()
    await confirmarIngreso(ANA, recargar)
    expect(recargar).toHaveBeenCalledTimes(1)
    expect(toastSuccess).toHaveBeenCalledWith("Ana Pérez ya figura como activo")
  })

  it("🔴 si la llamada falla NO avisa al listado", async () => {
    // Recargar igual dejaría la fila en su lugar y un toast de error al lado: el usuario no
    // sabría si el pedido salió. Peor todavía si el listado se hubiera filtrado en el cliente.
    const recargar = vi.fn()
    activarEmpleado.mockRejectedValue(new ApiError("no", "EMPLEADO_NO_ES_PREINGRESO", 409))
    await confirmarIngreso(ANA, recargar)
    expect(recargar).not.toHaveBeenCalled()
  })

  it("la página cablea ese aviso al `recargar` del listado, y no a un borrado local", () => {
    /*
     * La otra mitad de (b), y la única forma de verla sin DOM: leer el cable. El listado se pide
     * con `estado: "preingreso"`, así que al recargar la persona activada YA NO ENTRA en la
     * respuesta — la fila desaparece porque el backend deja de mandarla, no porque alguien la
     * saque del array. Con un filtrado local, el total del encabezado y la paginación (que los
     * cuenta el backend) quedarían diciendo uno de más.
     */
    const pagina = readFileSync(
      fileURLToPath(new URL("../../../app/(dashboard)/proximos-ingresos/page.tsx", import.meta.url)),
      "utf8",
    )
    expect(pagina).toContain("useActivarEmpleado(recargar)")
    expect(pagina).not.toContain("items.filter")
  })
})

describe("(c) el mensaje que se muestra es EL DEL BACKEND, no uno genérico", () => {
  const DEL_BACKEND =
    "El ingreso de Ana Pérez está previsto para el 03/09/2026. Si entró antes, corregí la " +
    "fecha en el legajo y después activala."

  it("un 400 INGRESO_AUN_NO_OCURRIO se muestra tal cual, con fecha y salida", async () => {
    activarEmpleado.mockRejectedValue(new ApiError(DEL_BACKEND, "INGRESO_AUN_NO_OCURRIO", 400))
    await confirmarIngreso(ANA, () => {})
    expect(toastError).toHaveBeenCalledWith(DEL_BACKEND)
  })

  it("y no aparece el genérico en su lugar", async () => {
    activarEmpleado.mockRejectedValue(new ApiError(DEL_BACKEND, "INGRESO_AUN_NO_OCURRIO", 400))
    await confirmarIngreso(ANA, () => {})
    expect(toastError).not.toHaveBeenCalledWith("No se pudo confirmar el ingreso.")
  })

  it("lo que NO es un ApiError sí cae al genérico: un 'Failed to fetch' no le dice nada a nadie", async () => {
    activarEmpleado.mockRejectedValue(new Error("Failed to fetch"))
    await confirmarIngreso(ANA, () => {})
    expect(toastError).toHaveBeenCalledWith("No se pudo confirmar el ingreso.")
  })
})
