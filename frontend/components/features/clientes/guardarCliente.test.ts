import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { createCliente, updateCliente } from "@/services/clientes"
import {
  guardarCliente, validarCliente, validarNombre, MAX_NOMBRE,
} from "@/components/features/clientes/guardarCliente"
import type { Cliente } from "@/types/cliente"

/**
 * EL BODY QUE SALE DEL FRONT — el eje que ningún test de este módulo miraba.
 *
 * Los tests de backend pasaban con el bug del `empresa_id: ""` VIVO, y sus fakes no tenían nada
 * de malo: **empezaban del lado de adentro de la validación**. Instanciaban el schema a mano, o
 * sea construían un valor válido que el front nunca producía. Acá se afirma lo que el front
 * MANDA.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?
 *
 * **1. 🔴 Los dobles de `createCliente`/`updateCliente` tendrían que ser `vi.fn()` mudos.** Guardan
 * el argumento entero y se afirma con `toEqual`, que es ESTRICTO con las claves de más: el body
 * se compara completo, no "se llamó". Si mañana alguien vuelve a agregarle un `empresa_id` al
 * payload, esto rojea — y ese es exactamente el hueco que produjo el 422 en producción (nadie
 * miraba el body que sale del front).
 *
 * **2. Faltaría el caso POSITIVO.** Un `guardarCliente` que no llamara NUNCA al service pasaría
 * los tests de "no manda". Por eso se afirman las dos direcciones.
 *
 * **3. El bloque estructural tendría que no existir.** `guardarCliente` es un módulo suelto: sin
 * verificar que `ClienteModal` lo USA y que no importa el service por su cuenta, estos tests
 * hablarían de un helper paralelo.
 *
 * ⚠️ NINGÚN TEST RENDERIZA `ClienteModal`. Usa `Dialog` de Radix, que monta por PORTAL, y con
 * vitest sin jsdom `renderToStaticMarkup` devuelve "": un test de ese componente pasaría con el
 * formulario entero borrado. Por eso las decisiones se prueban como funciones sueltas.
 */

vi.mock("@/services/clientes", () => ({
  createCliente: vi.fn(async () => ({ id: "c1" })),
  updateCliente: vi.fn(async () => ({ id: "c1" })),
}))

beforeEach(() => {
  vi.mocked(createCliente).mockClear()
  vi.mocked(updateCliente).mockClear()
})

describe("el alta manda solo el nombre", () => {
  it("🔴 el body ENTERO es { nombre }: sin empresa_id ni ningún otro campo", async () => {
    const errores = await guardarCliente({ nombre: "  Acme S.A.  " })

    expect(errores).toBeNull()
    expect(createCliente).toHaveBeenCalledTimes(1)
    // `toEqual` es estricto con las claves de más: una `empresa_id` que vuelva, rojea acá.
    expect(vi.mocked(createCliente).mock.calls[0][0]).toEqual({ nombre: "Acme S.A." })
  })

  it("un nombre inválido no sale a la red", async () => {
    const errores = await guardarCliente({ nombre: "   " })
    expect(createCliente).not.toHaveBeenCalled()
    expect(errores).toEqual({ nombre: "El nombre es requerido" })
  })

  it("un nombre demasiado largo tampoco", async () => {
    const errores = await guardarCliente({ nombre: "x".repeat(MAX_NOMBRE + 1) })
    expect(createCliente).not.toHaveBeenCalled()
    expect(errores).toEqual({ nombre: `Máximo ${MAX_NOMBRE} caracteres` })
  })
})

describe("la edición manda solo el nombre", () => {
  const CLIENTE: Cliente = {
    id: "c9", nombre: "Acme", activo: true,
    created_at: "2026-01-01T00:00:00Z", updated_at: null,
  }

  it("actualiza por id con el nombre trimmeado y nada más", async () => {
    const errores = await guardarCliente({ nombre: "  Acme SRL  " }, CLIENTE)

    expect(errores).toBeNull()
    expect(updateCliente).toHaveBeenCalledWith("c9", { nombre: "Acme SRL" })
    expect(createCliente).not.toHaveBeenCalled()
  })

  it("valida el nombre igual que el alta", async () => {
    const errores = await guardarCliente({ nombre: "" }, CLIENTE)
    expect(updateCliente).not.toHaveBeenCalled()
    expect(errores).toEqual({ nombre: "El nombre es requerido" })
  })
})

describe("validarCliente", () => {
  it("acepta un nombre normal y rechaza el vacío", () => {
    expect(validarCliente({ nombre: "Acme" })).toEqual({})
    expect(validarCliente({ nombre: "   " })).toEqual({ nombre: "El nombre es requerido" })
  })

  it("delega en validarNombre, que es la misma regla del alta y de la edición", () => {
    // Sin esto, `validarCliente` podría tener su propia copia de la regla y divergir.
    for (const n of ["", "   ", "Acme", "x".repeat(MAX_NOMBRE), "x".repeat(MAX_NOMBRE + 1)]) {
      const esperado = validarNombre(n)
      expect(validarCliente({ nombre: n })).toEqual(esperado ? { nombre: esperado } : {})
    }
  })
})

/**
 * 🔴 EL ÚNICO BLOQUE QUE SIGUE LEYENDO EL FUENTE, Y POR QUÉ NO SE PUEDE REESCRIBIR.
 *
 * Lo que afirma —"el modal no llama al service por su cuenta"— es una propiedad de la ESTRUCTURA
 * del módulo, no del comportamiento de ninguna función: no existe forma de observarla en runtime
 * sin renderizar `ClienteModal`, y renderizarlo es justamente lo imposible acá (Radix + portal +
 * vitest sin jsdom → markup vacío, ver el encabezado). Un test que no puede renderizar el
 * componente solo puede mirar su texto.
 *
 * Las otras cuatro assertions que este bloque tenía —`cliente-empresa`, `fetchEmpresas`,
 * `e.activa` y la línea de siembra con `getEmpresaActivaId()`— SÍ se borraron: afirmaban la
 * existencia del `<select>` de empresas, que dejó de existir. Estaba anotado en
 * `docs/DEUDA-TECNICA.md §5` como la tercera aparición del patrón "un test de texto sobre un
 * archivo convierte un refactor en cambio de contrato", con el disparador puesto en esta sesión.
 *
 * ⚠️ Lo que QUEDA sigue teniendo ese defecto: mover `ClienteModal.tsx` de path, o renombrar
 * `guardarCliente`, lo rompe sin que cambie el comportamiento. Se acepta a conciencia porque el
 * costo de la alternativa es mayor: sin esta guarda, todo lo de arriba podría estar describiendo
 * un helper que la pantalla no usa.
 */
describe("el modal usa esta puerta y no otra (estructural, ver la nota)", () => {
  const FUENTE = readFileSync(resolve(__dirname, "ClienteModal.tsx"), "utf-8")

  it("no está vacío (guarda: un fuente ilegible dejaría lo de abajo vacuo)", () => {
    expect(FUENTE.length).toBeGreaterThan(500)
    expect(FUENTE).toContain("export function ClienteModal")
  })

  it("🔴 no importa el service de alta: la única puerta es guardarCliente", () => {
    expect(FUENTE).not.toContain("createCliente")
    expect(FUENTE).toContain("guardarCliente")
  })

  it("ya no queda nada del selector de empresa", () => {
    // El reverso de las cuatro assertions borradas: no alcanza con dejar de exigirlas, hay que
    // afirmar que el bloque se fue. Si alguien lo reintroduce, el payload volvería a llevar una
    // empresa que el backend ya no acepta.
    for (const rastro of ["empresaId", "fetchEmpresas", "cliente-empresa", "getEmpresaActivaId"]) {
      expect(FUENTE).not.toContain(rastro)
    }
  })
})
