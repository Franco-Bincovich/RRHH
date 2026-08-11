import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"

import { EMPTY, validate } from "@/components/features/areas/areaForm"

/**
 * La validación del formulario de área, y el payload que sale del modal.
 *
 * 🔴 EL BUG QUE CIERRA: `AreaModal` armaba `empresa_id: empresaId ?? getEmpresaActivaId() ?? ""`
 * y NO validaba nada. Con el sidebar en "Todas las empresas" —el default— eso mandaba `""`, y
 * como `AreaCreate.empresa_id` era `str` en el backend, Pydantic lo aceptaba y el `""` moría en
 * Postgres como **500**.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS FALLEN?
 *
 * **1. `validate` tendría que recibir un solo argumento.** El segundo (`isEdit`) es lo que hace
 * falsable la asimetría: en el ALTA la empresa se exige, en la EDICIÓN no —`AreaUpdate` no la
 * lleva, un área no se muda de sociedad—. Con un solo caso, "exige siempre" y "exige en el alta"
 * serían indistinguibles, y exigirla en la edición rompería editar sin que nada lo dijera.
 *
 * **2. Faltaría el caso POSITIVO.** Un `validate` que devolviera error SIEMPRE pasaría los tests
 * de "rechaza el vacío". Se afirma que un form completo devuelve `{}`.
 *
 * ⚠️ NO se renderiza `AreaModal`: usa `Dialog` de Radix, que monta por PORTAL, y con vitest sin
 * jsdom `renderToStaticMarkup` devuelve "". Un test de ese componente pasaría con el formulario
 * entero borrado. Por eso la decisión se prueba como función suelta y el cableado con el bloque
 * estructural de abajo.
 */

const LLENO = { empresa_id: "8f3b1e2a-0000-4a1b-9c2d-111122223333", nombre: "Sistemas",
                descripcion: "", responsable_id: "" }

describe("validate — la empresa se exige solo en el alta", () => {
  it("🔴 alta sin empresa: rechaza", () => {
    expect(validate({ ...LLENO, empresa_id: "" }, false)).toEqual({ empresa_id: "Requerido" })
  })

  it("edición sin empresa: pasa (AreaUpdate no la lleva)", () => {
    expect(validate({ ...LLENO, empresa_id: "" }, true)).toEqual({})
  })

  it("alta completa: pasa", () => {
    expect(validate(LLENO, false)).toEqual({})
  })

  it("el nombre se sigue validando en las dos", () => {
    for (const isEdit of [true, false]) {
      expect(validate({ ...LLENO, nombre: "   " }, isEdit).nombre).toBe("El nombre es requerido")
      expect(validate({ ...LLENO, nombre: "x".repeat(101) }, isEdit).nombre)
        .toBe("Máximo 100 caracteres")
    }
  })

  it("EMPTY arranca sin empresa: es lo que el modal siembra en consolidado", () => {
    expect(EMPTY.empresa_id).toBe("")
    expect(validate(EMPTY, false).empresa_id).toBe("Requerido")
  })
})

/**
 * 🔴 EL CABLEADO. `areaForm` es un módulo suelto: sin verificar que `AreaModal` lo USA y que el
 * payload sale del form validado, esto hablaría de un helper paralelo.
 *
 * Es estructural porque no hay forma de observarlo en runtime sin renderizar el modal, y eso es
 * justamente lo imposible acá (Radix + portal + vitest sin jsdom).
 */
describe("el modal manda la empresa del form, no la del sidebar (estructural)", () => {
  const FUENTE = readFileSync(resolve(__dirname, "AreaModal.tsx"), "utf-8")
  // 🔗 Segundo fuente: el handler se mudó acá al bajar `AreaModal` de 151/150. Las dos
  // assertions que hablan del PAYLOAD y de la VALIDACIÓN se mudaron con él —enteras, no
  // debilitadas—, y las que hablan de la SIEMBRA se quedaron arriba. Mismo reparto que
  // `guardarCliente.test.ts`.
  const GUARDAR = readFileSync(resolve(__dirname, "guardarArea.ts"), "utf-8")

  it("no está vacío (guarda: un fuente ilegible dejaría lo de abajo vacuo)", () => {
    expect(FUENTE.length).toBeGreaterThan(500)
    expect(FUENTE).toContain("export function AreaModal")
    expect(GUARDAR.length).toBeGreaterThan(500)
    expect(GUARDAR).toContain("export async function guardarArea")
  })

  it("🔴 guardarArea es la ÚNICA puerta, y su payload sale del form ya validado", () => {
    // Las dos mitades son la misma invariante: el modal NO llama al service por su cuenta, y el
    // payload que sale lleva la empresa del form. Sin la primera, todo lo de arriba podría estar
    // describiendo un helper que la pantalla no usa.
    expect(FUENTE).not.toContain("createArea")
    expect(FUENTE).toContain("guardarArea")
    expect(GUARDAR).toContain("empresa_id: form.empresa_id")
  })

  it("🔴 el `?? \"\"` aparece UNA sola vez: en la siembra, no en el payload", () => {
    // El `?? ""` sobrevive para SEMBRAR el select, y está bien: entre la siembra y la red está
    // `validate`. Lo que no puede volver es un SEGUNDO uso, que sería el del payload.
    // Se cuenta en vez de usar `not.toContain`: el substring está en la línea legítima, así que
    // una aserción negativa sobre él no puede distinguir la buena de la mala.
    const usos = FUENTE.split("getEmpresaActivaId()").length - 1
    expect(usos, "getEmpresaActivaId() aparece más de una vez: ¿volvió al payload?").toBe(1)
    expect(FUENTE).toContain('setForm({ ...EMPTY, empresa_id: empresaId ?? getEmpresaActivaId() ?? "" })')
  })

  it("valida antes de mandar, y distingue alta de edición", () => {
    expect(GUARDAR).toContain("validate(form, Boolean(area))")
  })
})
