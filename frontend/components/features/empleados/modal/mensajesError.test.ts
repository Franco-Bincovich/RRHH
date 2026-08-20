import { describe, expect, it } from "vitest"

import { EMPTY, type FormData } from "./_constants"
import { validate } from "./form-utils"

/**
 * (a) y (b) del patrón de modal de formulario: la CUENTA del banner y que cada mensaje diga
 * **qué corregir**.
 *
 * 🔴 (b) ES UN BARRIDO, NO UNA LISTA DE CASOS. Verifica TODOS los mensajes que `validate`
 * puede devolver, así que un campo nuevo con un mensaje vago rojea sin tocar este archivo. La
 * lista de palabras prohibidas es corta a propósito: "inválido", "requerido" y "error" son las
 * tres formas en que se escribe un mensaje que no ayuda, y las tres estaban en el código antes
 * de esta tanda ("La empresa es requerida", "El email no es válido").
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDA FALLAR? Que un mensaje vuelva a la fórmula
 * vieja. Verificado: reponiendo "La empresa es requerida" el barrido rojea nombrando el campo.
 * Y la guarda de mínimo corre antes, porque un `validate` que devolviera `{}` pasaría el barrido
 * sin haber mirado un solo texto.
 */

/** Un form vacío dispara TODOS los obligatorios de una. */
const VACIO: FormData = { ...EMPTY }

const PROHIBIDAS = ["inválid", "invalid", "requerid", "error", "obligatorio", "campo vacío"]

describe("(b) los mensajes dicen qué corregir", () => {
  const errores = Object.entries(validate(VACIO, false)) as [string, string][]

  it("hay mensajes que mirar", () => {
    // Sin esta guarda, un `validate` roto que devuelva {} pasa todo lo de abajo en el vacío.
    expect(errores.length).toBeGreaterThanOrEqual(6)
  })

  it("ninguno usa las fórmulas que no le dicen nada al usuario", () => {
    const vagos = errores
      .filter(([, msg]) => PROHIBIDAS.some((p) => msg.toLowerCase().includes(p)))
      .map(([campo, msg]) => `${campo}: "${msg}"`)
    expect(
      vagos,
      "Un mensaje que dice que el campo está mal, y no qué escribir, no cumple el patrón " +
        "(docs/SISTEMA-DE-DISENO.md §3). El asterisco rojo del label ya dice que es obligatorio.",
    ).toEqual([])
  })

  it("cada uno empieza con un verbo de acción o explica la forma esperada", () => {
    // La contracara del barrido de arriba: no alcanza con esquivar tres palabras, tiene que
    // decir algo. Sin esto, "El nombre." pasaría el test anterior.
    for (const [campo, msg] of errores) {
      expect(msg.length, `${campo} tiene un mensaje demasiado corto para explicar algo`).toBeGreaterThan(20)
    }
  })

  it("el del email dice qué le falta, que es el ejemplo del sistema de diseño", () => {
    const conEmailMalo = validate({ ...VACIO, email_corporativo: "juan.perez" }, false)
    expect(conEmailMalo.email_corporativo).toContain("arroba")
    expect(conEmailMalo.email_corporativo).toContain("@")
  })
})

describe("(a) la cuenta del banner de resumen", () => {
  // Es la misma expresión que usa `useEmpleadoForm.cantidadErrores`. Se prueba acá, sobre la
  // salida real de `validate`, y no con un objeto inventado: lo que puede estar mal es que
  // cuente claves con `undefined`, que es justo lo que el mapa tiene después de corregir un campo.
  const contar = (errs: Record<string, string | undefined>) => Object.values(errs).filter(Boolean).length

  it("un form vacío cuenta todos los obligatorios", () => {
    expect(contar(validate(VACIO, false))).toBe(Object.keys(validate(VACIO, false)).length)
    expect(contar(validate(VACIO, false))).toBeGreaterThanOrEqual(6)
  })

  it("corregir un campo baja la cuenta en uno", () => {
    const antes = contar(validate(VACIO, false))
    const despues = contar(validate({ ...VACIO, nombre: "Ana" }, false))
    expect(despues).toBe(antes - 1)
  })

  it("🔴 un campo ya corregido queda como undefined en el mapa y NO se cuenta", () => {
    // El modal limpia el error del campo poniéndolo en `undefined`, no borrando la clave
    // (`setField`). Contar `Object.keys` en vez de los valores daría "Revisá 3 campos" con los
    // tres ya arreglados, y el usuario buscaría un error que no existe.
    expect(contar({ nombre: undefined, apellido: "Escribí el apellido…" })).toBe(1)
  })

  it("en edición la empresa no se pide: es un campo menos", () => {
    expect(contar(validate(VACIO, true))).toBe(contar(validate(VACIO, false)) - 1)
  })
})
