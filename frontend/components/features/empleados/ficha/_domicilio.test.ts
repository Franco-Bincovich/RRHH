import { describe, expect, it } from "vitest"

import { domicilioLegible, mostrarCrudo } from "@/components/features/empleados/ficha/_domicilio"
import type { Empleado } from "@/types/empleado"

/**
 * La ficha muestra el domicilio armado en una línea, no seis campos sueltos, y conserva el
 * texto libre viejo SOLO mientras los estructurados estén vacíos — para que alguien pueda
 * completarlos mirándolo.
 *
 * Con 0 domicilios cargados en producción esto no rescata nada hoy: cubre lo que se cargue a
 * mano de acá en adelante.
 */

function emp(over: Partial<Empleado> = {}): Empleado {
  return {
    domicilio: null, domicilio_calle: null, domicilio_numero: null,
    domicilio_piso_depto: null, domicilio_localidad: null, domicilio_provincia: null,
    domicilio_cp: null, ...over,
  } as Empleado
}

describe("domicilio armado", () => {
  it("junta calle y número, y separa el resto con comas", () => {
    expect(domicilioLegible(emp({
      domicilio_calle: "Av. Rivadavia", domicilio_numero: "1234",
      domicilio_piso_depto: "4 B", domicilio_localidad: "Bell Ville",
      domicilio_cp: "2550", domicilio_provincia: "Córdoba",
    }))).toBe("Av. Rivadavia 1234, 4 B, Bell Ville, 2550, Córdoba")
  })

  it("sin nada cargado devuelve null", () => {
    expect(domicilioLegible(emp())).toBeNull()
  })

  it("con carga parcial no deja comas colgando", () => {
    // El modo de falla feo: ", , Bell Ville, , Córdoba".
    const out = domicilioLegible(emp({
      domicilio_localidad: "Bell Ville", domicilio_provincia: "Córdoba",
    }))
    expect(out).toBe("Bell Ville, Córdoba")
    expect(out).not.toMatch(/^,|,\s*,|,\s*$/)
  })

  it("solo la calle, sin número, se lee bien", () => {
    expect(domicilioLegible(emp({ domicilio_calle: "Ruta 9" }))).toBe("Ruta 9")
  })

  it("solo el número no inventa espacio adelante", () => {
    expect(domicilioLegible(emp({ domicilio_numero: "S/N" }))).toBe("S/N")
  })
})

describe("el texto libre viejo como referencia", () => {
  it("se muestra si hay crudo y los estructurados están vacíos", () => {
    expect(mostrarCrudo(emp({ domicilio: "Rivadavia 1234, Bell Ville" }))).toBe(true)
  })

  it("se oculta una vez que los estructurados tienen algo", () => {
    // Mostrar los dos dejaría dos direcciones que pueden no coincidir, sin saber cuál rige.
    expect(mostrarCrudo(emp({
      domicilio: "Rivadavia 1234, Bell Ville", domicilio_localidad: "Bell Ville",
    }))).toBe(false)
  })

  it("no se muestra si no hay crudo", () => {
    expect(mostrarCrudo(emp())).toBe(false)
  })

  it("un crudo de solo espacios no cuenta como referencia", () => {
    expect(mostrarCrudo(emp({ domicilio: "   " }))).toBe(false)
  })
})
