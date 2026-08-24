/**
 * El 404 y el 500 no son el mismo cartel.
 *
 * 🔴 POR QUÉ IMPORTA MÁS QUE UN COPY: el 404 es TAMBIÉN lo que responde el backend cuando el
 * recurso es de OTRA EMPRESA — el contrato de la barrera de empresa exige que "no existe" y
 * "es de otra empresa" se vean idénticos, así que este caso lo va a ver alguien de RRHH que
 * abrió un link con el selector de empresa en otra sociedad. Decirle "Algo salió mal" y
 * ofrecerle "Reintentar" lo deja apretando un botón que no puede funcionar.
 *
 * ⚠️ Qué tendría que ser distinto para que estos tests puedan fallar: se construyen ApiError
 * REALES con status 404 y 500, así que la distinción se toma del mismo objeto que produce el
 * cliente HTTP. Con la implementación vieja —un solo título y un botón siempre "Reintentar"—
 * rojean todos los del primer bloque. Verificado por mutación.
 *
 * Se renderiza a string con react-dom/server porque el proyecto corre vitest SIN jsdom.
 */
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { ErrorState, esNoEncontrado } from "@/components/ui/ErrorState"
import { ApiError } from "@/services/api"

const NO_ENCONTRADO = new ApiError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
const ROTO = new ApiError("Error interno", "INTERNAL_ERROR", 500)

describe("esNoEncontrado", () => {
  it("solo un ApiError 404", () => {
    expect(esNoEncontrado(NO_ENCONTRADO)).toBe(true)
    expect(esNoEncontrado(ROTO)).toBe(false)
  })

  it("un string no alcanza: no lleva status", () => {
    // Varias pantallas guardan `error` como texto. Ahí no hay 404 que detectar, y tratar de
    // adivinarlo por el mensaje sería peor que no hacerlo.
    expect(esNoEncontrado("No se encontró el empleado")).toBe(false)
    expect(esNoEncontrado(null)).toBe(false)
    expect(esNoEncontrado(new Error("boom"))).toBe(false)
  })
})

describe("404", () => {
  const html = renderToStaticMarkup(
    <ErrorState error={NO_ENCONTRADO} action={vi.fn()} onVolver={vi.fn()} />
  )

  it("dice que no se encontró, no que algo salió mal", () => {
    expect(html).toContain("No se encontró")
    expect(html).not.toContain("Algo salió mal")
  })

  it("ofrece Volver y NO Reintentar, aunque la pantalla pase las dos", () => {
    expect(html).toContain("Volver")
    expect(html).not.toContain("Reintentar")
  })

  it("nombra el caso de la otra empresa sin confirmarlo", () => {
    // El contrato de la barrera de empresa: no se puede decir "es de otra empresa" (sería
    // confirmar que existe), pero sí se puede mandar a revisar el selector.
    expect(html).toContain("empresa seleccionada")
    expect(html).not.toMatch(/pertenece a otra empresa|es de otra empresa|sin permiso/i)
  })

  it("sin salida declarada no pinta botón: ninguno es mejor que uno que miente", () => {
    const solo = renderToStaticMarkup(<ErrorState error={NO_ENCONTRADO} action={vi.fn()} />)
    expect(solo).not.toContain("Reintentar")
    expect(solo).not.toContain("Volver")
  })
})

describe("el resto de los errores no cambian", () => {
  it("un 500 sigue diciendo que algo salió mal y ofrece Reintentar", () => {
    const html = renderToStaticMarkup(<ErrorState error={ROTO} action={vi.fn()} />)
    expect(html).toContain("Algo salió mal")
    expect(html).toContain("Reintentar")
  })

  it("sin `error` se comporta como siempre (las pantallas que no lo pasan no cambian)", () => {
    const html = renderToStaticMarkup(<ErrorState action={vi.fn()} />)
    expect(html).toContain("Algo salió mal")
    expect(html).toContain("Reintentar")
  })

  it("un título o descripción explícitos siguen ganando", () => {
    const html = renderToStaticMarkup(
      <ErrorState error={NO_ENCONTRADO} description="No se pudo cargar la empresa." onVolver={vi.fn()} />
    )
    expect(html).toContain("No se pudo cargar la empresa.")
  })

  it("una pantalla sin recarga puede ofrecer solo Volver", () => {
    const html = renderToStaticMarkup(<ErrorState error={ROTO} onVolver={vi.fn()} />)
    expect(html).toContain("Volver")
    expect(html).not.toContain("Reintentar")
  })
})
