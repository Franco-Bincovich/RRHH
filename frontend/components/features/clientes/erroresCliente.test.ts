import { describe, expect, it } from "vitest"

import { ApiError } from "@/services/api"
import { mensajeDeError } from "@/components/features/clientes/erroresCliente"
import { MAX_NOMBRE, validarNombre } from "@/components/features/clientes/guardarCliente"

/**
 * Las dos decisiones del formulario, testeadas como funciones puras.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * Que los dos casos de `mensajeDeError` devolvieran lo mismo. Se prueban los DOS: un ApiError
 * (mensaje del backend, que hay que conservar) y un Error común (genérico). Con un solo caso,
 * una implementación que devolviera siempre el genérico pasaría — y ese es justamente el bug:
 * el único error de negocio de esta pantalla es CLIENTE_DUPLICADO, cuyo texto le dice al usuario
 * qué hacer. Tragarlo lo deja apretando "Crear" sin entender por qué no pasa nada.
 *
 * NO se renderiza `ClienteModal`: usa `Dialog` de Radix, que monta por PORTAL, y con vitest sin
 * jsdom `renderToStaticMarkup` devuelve "". Un test de ese componente pasaría con el formulario
 * entero borrado. Por eso las dos decisiones se exportan sueltas y se prueban acá.
 *
 * ⚠️ `validarNombre` y `MAX_NOMBRE` se mudaron de `ClienteModal` a `guardarCliente` al cerrar el
 * bug del `empresa_id: ""`: ahora TODA la decisión de guardar vive junta. El resto del envío se
 * prueba en `guardarCliente.test.ts`.
 */

describe("mensajeDeError", () => {
  it("conserva el mensaje del backend", () => {
    const e = new ApiError("Ya existe un cliente con ese nombre en la empresa", "CLIENTE_DUPLICADO", 409)
    expect(mensajeDeError(e)).toBe("Ya existe un cliente con ese nombre en la empresa")
  })

  it("usa un genérico solo para lo que no es un error de la API", () => {
    expect(mensajeDeError(new Error("network"))).toBe("No se pudo guardar. Intentá de nuevo.")
    expect(mensajeDeError(undefined)).toBe("No se pudo guardar. Intentá de nuevo.")
  })
})

describe("validarNombre", () => {
  it("acepta un nombre normal", () => {
    expect(validarNombre("Acme S.A.")).toBe("")
  })

  it("rechaza vacío y solo espacios", () => {
    // El backend también lo rechaza (NOMBRE_REQUERIDO 422); esto evita el viaje.
    expect(validarNombre("")).toBe("El nombre es requerido")
    expect(validarNombre("   ")).toBe("El nombre es requerido")
  })

  it("rechaza por encima del máximo, que es el del schema del backend", () => {
    expect(validarNombre("x".repeat(MAX_NOMBRE))).toBe("")
    expect(validarNombre("x".repeat(MAX_NOMBRE + 1))).toBe(`Máximo ${MAX_NOMBRE} caracteres`)
  })
})
