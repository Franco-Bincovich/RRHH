// El mensaje que ve el usuario cuando un export falla.
//
// Antes este componente hacía `catch { toast.error("No se pudo exportar. Intentá de nuevo.") }`
// y descartaba el error. Con el tope de filas de B7 eso importa: el backend arma un mensaje que
// dice cuántas filas hay, cuál es el máximo y qué hacer, y el genérico lo tiraba — mostrando
// además el consejo equivocado, porque reintentar no baja el total.
//
// Se testea la función y no el click: el proyecto corre vitest con environment "node" y sin
// jsdom, así que no hay forma de disparar el menú. La decisión de qué mensaje mostrar es toda
// la lógica que había.
import { describe, expect, it } from "vitest"

import { ApiError } from "@/services/api"
import { mensajeDeError } from "@/components/features/export/ExportMenu"

const GENERICO = "No se pudo exportar. Intentá de nuevo."

describe("mensajeDeError", () => {
  it("muestra el mensaje del backend cuando es un ApiError", () => {
    const e = new ApiError(
      "La consulta devuelve 12.345 filas y el máximo por archivo es 5.000. Usá los filtros de la pantalla para acotar el resultado y volvé a exportar.",
      "EXPORT_DEMASIADAS_FILAS", 422,
    )
    expect(mensajeDeError(e)).toBe(e.message)
  })

  it("el mensaje del límite llega entero, con los dos números", () => {
    const e = new ApiError("La consulta devuelve 12.345 filas y el máximo por archivo es 5.000.", "EXPORT_DEMASIADAS_FILAS", 422)
    const msg = mensajeDeError(e)
    expect(msg).toContain("12.345")
    expect(msg).toContain("5.000")
  })

  it("no muestra el genérico cuando hay mensaje del backend", () => {
    const e = new ApiError("Algo puntual", "OTRO_CODE", 400)
    expect(mensajeDeError(e)).not.toBe(GENERICO)
  })

  it("cae al genérico con un error que no es de la API", () => {
    // Red caída, JSON roto: ahí reintentar SÍ es el consejo correcto.
    expect(mensajeDeError(new TypeError("Failed to fetch"))).toBe(GENERICO)
  })

  it("cae al genérico con algo que ni siquiera es un Error", () => {
    expect(mensajeDeError("boom")).toBe(GENERICO)
    expect(mensajeDeError(undefined)).toBe(GENERICO)
  })
})
