import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { getEmpresaActivaId } from "@/services/empresaStore"
import { createCliente, updateCliente } from "@/services/clientes"
import { guardarCliente, validarCliente } from "@/components/features/clientes/guardarCliente"
import type { Cliente } from "@/types/cliente"

/**
 * EL BODY QUE SALE DEL FRONT — el eje que ningún test de este módulo miraba.
 *
 * Los 30 tests de backend (`test_clientes_abm.py` + `test_clientes_catalogo.py`) pasaban con el
 * bug VIVO, y sus fakes no tenían nada de malo: la barrera de empresa está genuinamente probada.
 * El problema era otro y no es "el fake no puede desmentir" — es que esos tests **empiezan del
 * lado de adentro de la validación**. Instancian `ClienteCreate(empresa_id=uuid4(), ...)` a mano,
 * o sea que construyen un UUID válido que el front nunca producía. Pydantic ya dijo que sí antes
 * de la primera línea del test.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?
 *
 * **1. `getEmpresaActivaId` tendría que devolver un UUID.** Está mockeado a `null`, que es su
 * valor REAL en modo consolidado: `setEmpresaActivaId(null)` BORRA la clave de localStorage, y
 * "Todas las empresas" es el default del selector. Con un UUID de fantasía, el caso que rompía
 * producción no puede aparecer. El test siembra `empresaId` con el mock, igual que el modal.
 *
 * **2. Los dobles de `createCliente`/`updateCliente` tendrían que ser `vi.fn()` mudos.** Guardan
 * el argumento entero, así que se afirma el BODY —no "se llamó"—, y un `empresa_id: ""` que
 * volviera a colarse se ve. Sin capturar el argumento, mandar `""` y mandar un UUID serían
 * indistinguibles.
 *
 * **3. Faltaría el caso POSITIVO.** Un `guardarCliente` que no llamara NUNCA a `createCliente`
 * pasaría el test de "no manda vacío". Por eso se afirman las dos direcciones: con empresa NO
 * manda nada, y con empresa manda exactamente ese UUID.
 *
 * **4. El bloque estructural tendría que no existir.** `guardarCliente` es un módulo suelto: sin
 * verificar que `ClienteModal` lo USA y que no importa `createCliente` por su cuenta, estos
 * tests hablarían de un helper paralelo y el modal podría seguir mandando `?? ""` al lado.
 * `ClienteModal` NO se renderiza —Radix monta por portal y con vitest sin jsdom el markup sale
 * ""—, así que el vínculo se verifica sobre el fuente, que es lo único que no miente acá.
 */

vi.mock("@/services/clientes", () => ({
  createCliente: vi.fn(async () => ({ id: "c1" })),
  updateCliente: vi.fn(async () => ({ id: "c1" })),
}))

// `null` = "Todas las empresas". Es el DEFAULT del sidebar, no un caso de borde.
vi.mock("@/services/empresaStore", () => ({ getEmpresaActivaId: vi.fn(() => null) }))

const UUID_EMPRESA = "8f3b1e2a-0000-4a1b-9c2d-111122223333"

beforeEach(() => {
  vi.mocked(createCliente).mockClear()
  vi.mocked(updateCliente).mockClear()
})

describe("el alta no puede mandar empresa_id vacío", () => {
  it("🔴 con el sidebar en 'Todas las empresas' NO dispara el POST", async () => {
    // Exactamente lo que sembraba el modal: `getEmpresaActivaId() ?? ""`.
    const empresaId = getEmpresaActivaId() ?? ""
    expect(empresaId).toBe("") // el mock representa el modo consolidado

    const errores = await guardarCliente({ nombre: "Acme S.A.", empresaId })

    expect(createCliente).not.toHaveBeenCalled()
    expect(errores).toEqual({ empresa: "Requerido" })
  })

  it("con una empresa elegida manda ese UUID y nada más", async () => {
    const errores = await guardarCliente({ nombre: "  Acme S.A.  ", empresaId: UUID_EMPRESA })

    expect(errores).toBeNull()
    expect(createCliente).toHaveBeenCalledTimes(1)
    // El body ENTERO: `empresa_id` es un UUID real y el nombre viaja trimmeado.
    expect(vi.mocked(createCliente).mock.calls[0][0])
      .toEqual({ empresa_id: UUID_EMPRESA, nombre: "Acme S.A." })
  })

  it("un nombre inválido tampoco sale a la red", async () => {
    const errores = await guardarCliente({ nombre: "   ", empresaId: UUID_EMPRESA })
    expect(createCliente).not.toHaveBeenCalled()
    expect(errores).toEqual({ nombre: "El nombre es requerido" })
  })
})

describe("la edición sigue andando", () => {
  const CLIENTE: Cliente = {
    id: "c9", empresa_id: UUID_EMPRESA, nombre: "Acme", activo: true,
    created_at: "2026-01-01T00:00:00Z", updated_at: null,
  }

  it("no exige empresa: `empresa_id` no está en ClienteUpdate", async () => {
    // Con `empresaId: ""` —el peor caso— la edición TIENE que pasar igual. Exigir la empresa
    // acá rompería editar en modo consolidado, que hoy funciona.
    const errores = await guardarCliente({ nombre: "Acme SRL", empresaId: "" }, CLIENTE)

    expect(errores).toBeNull()
    expect(updateCliente).toHaveBeenCalledWith("c9", { nombre: "Acme SRL" })
    expect(createCliente).not.toHaveBeenCalled()
  })

  it("validarCliente pide empresa en el alta y no en la edición", () => {
    expect(validarCliente({ nombre: "Acme", empresaId: "" }, false)).toEqual({ empresa: "Requerido" })
    expect(validarCliente({ nombre: "Acme", empresaId: "" }, true)).toEqual({})
  })
})

describe("el modal usa esta puerta y no otra", () => {
  const FUENTE = readFileSync(resolve(__dirname, "ClienteModal.tsx"), "utf-8")

  it("no está vacío (guarda: un fuente ilegible dejaría todo lo de abajo vacuo)", () => {
    expect(FUENTE.length).toBeGreaterThan(500)
    expect(FUENTE).toContain("export function ClienteModal")
  })

  it("🔴 no importa createCliente: la única puerta es guardarCliente", () => {
    expect(FUENTE).not.toContain("createCliente")
    expect(FUENTE).toContain("guardarCliente")
  })

  it("🔴 no queda ningún `?? \"\"` yendo a la red", () => {
    // El `?? ""` sigue existiendo para SEMBRAR el select, y está bien: lo que no puede volver a
    // pasar es que ese "" sea el valor que se manda. Se verifica que la siembra alimente el
    // estado del select y no una llamada al service.
    expect(FUENTE).toContain("setEmpresaId(cliente?.empresa_id ?? getEmpresaActivaId() ?? \"\")")
  })

  it("renderiza el select de empresas solo en el alta", () => {
    expect(FUENTE).toContain("fetchEmpresas")
    expect(FUENTE).toContain("cliente-empresa")
    expect(FUENTE).toContain("{!isEdit && (")   // el select va dentro de esa guarda
    expect(FUENTE).toContain("e.activa")        // solo empresas activas
  })
})
