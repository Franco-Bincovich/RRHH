import { renderToStaticMarkup } from "react-dom/server"
import { afterEach, describe, expect, it, vi } from "vitest"

/**
 * El sueldo es un dato de COSTOS y la ficha vive bajo EMPLEADOS: la sección no se renderiza
 * si el rol no puede leer costos.
 *
 * Que el backend la gatee no alcanza. Una sección que aparece y falla es peor que una que no
 * aparece: el usuario ve un bloque roto y no sabe si es un permiso o un error del sistema.
 * Hoy no existe un rol con EMPLEADOS y sin COSTOS —así que esto no cambia nada para nadie—,
 * pero el día que exista, la ficha no puede volverse la puerta de atrás a los sueldos.
 *
 * Se renderiza a string con react-dom/server porque el proyecto corre vitest SIN jsdom.
 * Alcanza: lo que se verifica es qué sale y qué no, no la interacción.
 */

const fetchHistorialSalarial = vi.fn(() => new Promise(() => {}))
vi.mock("@/services/costos", () => ({ fetchHistorialSalarial }))

const puede = vi.fn()
vi.mock("@/services/permisos", () => ({
  puede: (...a: unknown[]) => puede(...a),
  getRol: () => "un_rol",
  seccionDeRuta: () => null,
}))
vi.mock("next/navigation", () => ({ usePathname: () => "/empleados/abc" }))

const { HistorialSalarialSection, debeCargar } = await import(
  "@/components/features/empleados/ficha/HistorialSalarialSection"
)

afterEach(() => {
  puede.mockReset()
  fetchHistorialSalarial.mockClear()
})

function render(puedeLeerCostos: boolean): string {
  puede.mockReturnValue(puedeLeerCostos)
  return renderToStaticMarkup(<HistorialSalarialSection empleadoId="abc" />)
}

describe("gate de sección", () => {
  it("sin permiso de costos no renderiza nada", () => {
    expect(render(false)).toBe("")
  })

  it("con permiso renderiza la sección", () => {
    expect(render(true)).toContain("Historial salarial")
  })

  it("consulta el permiso de COSTOS, no el de la ruta", () => {
    render(true)
    expect(puede).toHaveBeenCalledWith("un_rol", "costos", "read")
  })

  it("sin permiso tampoco pide los datos al backend", () => {
    // Se verifica sobre `debeCargar` y NO sobre el mock del fetch: sin jsdom los efectos no
    // corren, así que "no llamó al fetch" pasaría igual con el guard borrado.
    expect(debeCargar("abc", false)).toBe(false)
  })

  it("con permiso sí los pide", () => {
    expect(debeCargar("abc", true)).toBe(true)
  })

  it("sin empleado no pide nada, tenga o no permiso", () => {
    expect(debeCargar("", true)).toBe(false)
  })
})

describe("estados", () => {
  it("arranca en carga, no en vacío", () => {
    // Mostrar "no hay sueldos" mientras carga haría creer que el empleado no tiene nómina.
    expect(render(true)).not.toContain("Todavía no hay sueldos")
  })
})
