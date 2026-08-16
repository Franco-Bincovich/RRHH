import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { createEvento, updateEvento } from "@/services/eventos"
import {
  diasAvisoNumero, guardarEvento, validarEvento, MAX_DIAS_AVISO, MAX_NOMBRE, type FormEvento,
} from "@/components/features/eventos/guardarEvento"
import type { Evento } from "@/types/evento"

/**
 * EL BODY QUE SALE DEL FRONT, y en particular el `dias_aviso`.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?
 *
 * **1. 🔴 Los dobles guardan el argumento ENTERO y se afirma con `toEqual`**, que es estricto con
 * las claves de más. Un `vi.fn()` mudo dejaría pasar cualquier payload y el test solo diría "se
 * llamó", que es justo lo que no alcanzó en clientes (el `empresa_id: ""` que rompió el alta en
 * producción viajaba sin que ningún test mirara el body).
 *
 * **2. 🔴 Los casos de `dias_aviso` distinguen VACÍO de CERO, y son distintos entre sí.** Con un
 * solo caso, "vacío se manda como undefined" y "vacío se manda como 0" serían indistinguibles —
 * y son dos comportamientos opuestos: `undefined` le pide al backend el default de la empresa
 * (21 días, pongamos) y `0` le dice "avisá el mismo día". `Number("")` es 0, así que la
 * confusión es el default del lenguaje, no un descuido improbable.
 *
 * **3. El caso POSITIVO.** Un `guardarEvento` que no llamara nunca al service pasaría todos los
 * tests de "no manda". Se afirman las dos direcciones.
 *
 * ⚠️ NINGÚN TEST RENDERIZA `EventoModal`. Usa `Dialog` de Radix, que monta por PORTAL, y con
 * vitest sin jsdom `renderToStaticMarkup` devuelve "": un test de ese componente pasaría con el
 * formulario entero borrado. Por eso las decisiones se prueban como funciones sueltas.
 */

vi.mock("@/services/eventos", () => ({
  createEvento: vi.fn(async () => ({ id: "e1" })),
  updateEvento: vi.fn(async () => ({ id: "e1" })),
}))

beforeEach(() => {
  vi.mocked(createEvento).mockClear()
  vi.mocked(updateEvento).mockClear()
})

const BASE: FormEvento = {
  nombre: "Feriado puente", fecha: "2026-12-08", descripcion: "", diasAviso: "", esPublica: true,
}

describe("el alta manda el body completo", () => {
  it("con el nombre y la descripción trimmeados", async () => {
    const errores = await guardarEvento({
      ...BASE, nombre: "  Feriado puente  ", descripcion: "  Nota  ", diasAviso: "5",
    })

    expect(errores).toBeNull()
    expect(vi.mocked(createEvento).mock.calls[0][0]).toEqual({
      nombre: "Feriado puente", fecha: "2026-12-08", descripcion: "Nota",
      dias_aviso: 5, es_publica: true,
    })
  })

  it("🔴 con el campo de aviso VACÍO manda `undefined`, no 0", async () => {
    // `undefined` es lo que hace que el backend aplique el default de la empresa. Un 0 acá
    // congelaría "avisar el mismo día" en la fila y la pantalla de Configuración no movería nada.
    await guardarEvento({ ...BASE, diasAviso: "" })
    expect(vi.mocked(createEvento).mock.calls[0][0].dias_aviso).toBeUndefined()
  })

  it("🔴 con el aviso en CERO manda 0, que es un valor legítimo", async () => {
    await guardarEvento({ ...BASE, diasAviso: "0" })
    expect(vi.mocked(createEvento).mock.calls[0][0].dias_aviso).toBe(0)
  })

  it("marcar 'solo para mí' viaja como es_publica false", async () => {
    await guardarEvento({ ...BASE, esPublica: false })
    expect(vi.mocked(createEvento).mock.calls[0][0].es_publica).toBe(false)
  })
})

describe("lo inválido no sale a la red", () => {
  it("sin nombre", async () => {
    const errores = await guardarEvento({ ...BASE, nombre: "   " })
    expect(createEvento).not.toHaveBeenCalled()
    expect(errores).toEqual({ nombre: "El nombre es requerido" })
  })

  it("sin fecha", async () => {
    const errores = await guardarEvento({ ...BASE, fecha: "" })
    expect(createEvento).not.toHaveBeenCalled()
    expect(errores).toEqual({ fecha: "La fecha es requerida" })
  })

  it("con el nombre demasiado largo", async () => {
    const errores = await guardarEvento({ ...BASE, nombre: "x".repeat(MAX_NOMBRE + 1) })
    expect(createEvento).not.toHaveBeenCalled()
    expect(errores?.nombre).toBe(`Máximo ${MAX_NOMBRE} caracteres`)
  })

  it("con el aviso fuera del rango del CHECK", async () => {
    const errores = await guardarEvento({ ...BASE, diasAviso: String(MAX_DIAS_AVISO + 1) })
    expect(createEvento).not.toHaveBeenCalled()
    expect(errores?.diasAviso).toBeTruthy()
  })

  it("🔴 con un aviso que no es un número: avisa en vez de guardarlo con el default", async () => {
    // Sin esta validación, `diasAvisoNumero("abc")` da `undefined` y el evento se guardaría en
    // silencio con el default de la empresa — el usuario escribió algo y nadie le dijo nada.
    const errores = await guardarEvento({ ...BASE, diasAviso: "abc" })
    expect(createEvento).not.toHaveBeenCalled()
    expect(errores?.diasAviso).toBeTruthy()
  })
})

describe("la edición", () => {
  const EVENTO: Evento = {
    id: "e9", empresa_id: "emp1", nombre: "Feriado", fecha: "2026-12-08", descripcion: null,
    dias_aviso: 7, es_publica: true, resuelta: false, resuelta_at: null, resuelta_por: null,
    resuelta_por_nombre: null, created_by: "u1", created_by_nombre: null, empresa_nombre: null,
    created_at: "2026-01-01T00:00:00Z", updated_at: null,
  }

  it("actualiza por id y no crea", async () => {
    const errores = await guardarEvento({ ...BASE, nombre: "Otro", diasAviso: "3" }, EVENTO)
    expect(errores).toBeNull()
    expect(createEvento).not.toHaveBeenCalled()
    expect(vi.mocked(updateEvento).mock.calls[0][0]).toBe("e9")
    expect(vi.mocked(updateEvento).mock.calls[0][1].dias_aviso).toBe(3)
  })

  it("valida igual que el alta", async () => {
    const errores = await guardarEvento({ ...BASE, fecha: "" }, EVENTO)
    expect(updateEvento).not.toHaveBeenCalled()
    expect(errores).toEqual({ fecha: "La fecha es requerida" })
  })
})

describe("diasAvisoNumero", () => {
  it("distingue vacío de cero", () => {
    expect(diasAvisoNumero("")).toBeUndefined()
    expect(diasAvisoNumero("   ")).toBeUndefined()
    expect(diasAvisoNumero("0")).toBe(0)
  })

  it("y el validador usa el TEXTO, no el número ya convertido", () => {
    // Si `validarEvento` llamara a `diasAvisoNumero` primero, "abc" sería `undefined` y pasaría
    // como "no lo cargué". Esta pareja de aserciones es lo que fija que son dos lecturas
    // distintas del mismo campo.
    expect(diasAvisoNumero("abc")).toBeUndefined()
    expect(validarEvento({ ...BASE, diasAviso: "abc" }).diasAviso).toBeTruthy()
  })
})

/**
 * 🔴 EL ÚNICO BLOQUE QUE LEE EL FUENTE, y por el mismo motivo que en clientes: lo que afirma es
 * una propiedad de la ESTRUCTURA del módulo —"el modal no llama al service por su cuenta"— y no
 * hay forma de observarla en runtime sin renderizar `EventoModal`, que con Radix + portal +
 * vitest sin jsdom sale como markup vacío. Sin esta guarda, todo lo de arriba podría estar
 * describiendo un helper que la pantalla no usa.
 *
 * ⚠️ Tiene el defecto conocido: mover el archivo o renombrar la función lo rompe sin que cambie
 * el comportamiento. Se acepta a conciencia, igual que en `guardarCliente.test.ts`.
 */
describe("el modal usa esta puerta y no otra (estructural, ver la nota)", () => {
  const FUENTE = readFileSync(resolve(__dirname, "EventoModal.tsx"), "utf-8")

  it("no está vacío (guarda: un fuente ilegible dejaría lo de abajo vacuo)", () => {
    expect(FUENTE.length).toBeGreaterThan(500)
    expect(FUENTE).toContain("export function EventoModal")
  })

  it("🔴 no importa los services de escritura: la única puerta es guardarEvento", () => {
    expect(FUENTE).not.toContain("createEvento")
    expect(FUENTE).not.toContain("updateEvento")
    expect(FUENTE).toContain("guardarEvento")
  })
})
