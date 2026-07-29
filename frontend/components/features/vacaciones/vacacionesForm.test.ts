import { describe, it, expect } from "vitest"

import {
  EMPTY_VACACION, calcDias, diasDelForm, payloadPendiente, payloadTomada, validateVacacion,
  type VacacionFormData,
} from "./vacacionesForm"

/**
 * Lógica pura del form de vacaciones. Lo que importa acá es el RUTEO: el tilde "No se tomó"
 * decide a qué TABLA va el registro, así que un error en esta función manda días con fechas a
 * la tabla sin fechas (o al revés) sin que nada falle.
 *
 * Los payloads se comparan contra lo DERIVADO del form, no contra constantes escritas a mano
 * donde eso pueda esconder el bug.
 */
const base = (over: Partial<VacacionFormData> = {}): VacacionFormData => ({
  ...EMPTY_VACACION, empleado_id: "emp-1", empresa_id: "empresa-1", periodo: "2025", ...over,
})

describe("calcDias / diasDelForm", () => {
  it("cuenta los extremos incluidos", () => {
    expect(calcDias("2026-04-13", "2026-04-19")).toBe(7)
  })

  it("devuelve 0 con rango incompleto o invertido", () => {
    expect(calcDias("", "2026-04-19")).toBe(0)
    expect(calcDias("2026-04-19", "2026-04-13")).toBe(0)
  })

  it("los días de un pendiente salen del campo, no de las fechas", () => {
    // Para que falle: que diasDelForm mire las fechas también cuando pendiente=true. Un
    // pendiente NO tiene fechas, así que caería siempre en 0.
    const form = base({ pendiente: true, dias_pendientes: "10", fecha_desde: "", fecha_hasta: "" })
    expect(diasDelForm(form)).toBe(10)
  })
})

describe("validateVacacion — el tilde cambia qué se exige", () => {
  it("sin tildar exige fechas y NO cantidad de días", () => {
    const errs = validateVacacion(base({ pendiente: false }), true)
    expect(errs.fecha_desde).toBeDefined()
    expect(errs.fecha_hasta).toBeDefined()
    expect(errs.dias_pendientes).toBeUndefined()
  })

  it("tildado exige cantidad de días y NO fechas", () => {
    // Es la aserción central del diseño: un pendiente sin fechas tiene que ser VÁLIDO.
    // Para que falle: que la validación de fechas corra igual con pendiente=true.
    const errs = validateVacacion(base({ pendiente: true, dias_pendientes: "10" }), true)
    expect(errs.fecha_desde).toBeUndefined()
    expect(errs.fecha_hasta).toBeUndefined()
    expect(errs.dias_pendientes).toBeUndefined()
    expect(Object.keys(errs)).toHaveLength(0)
  })

  it("rechaza días pendientes vacíos, cero, negativos y no enteros", () => {
    for (const dias of ["", "0", "-3", "1.5"]) {
      const errs = validateVacacion(base({ pendiente: true, dias_pendientes: dias }), true)
      expect(errs.dias_pendientes, `dias="${dias}"`).toBeDefined()
    }
  })

  it("el período es obligatorio y acotado en los dos casos", () => {
    for (const pendiente of [true, false]) {
      const form = base({ pendiente, dias_pendientes: "5", fecha_desde: "2026-04-13", fecha_hasta: "2026-04-19" })
      expect(validateVacacion({ ...form, periodo: "" }, true).periodo).toBeDefined()
      expect(validateVacacion({ ...form, periodo: "1999" }, true).periodo).toBeDefined()
      expect(validateVacacion({ ...form, periodo: "2101" }, true).periodo).toBeDefined()
      expect(validateVacacion({ ...form, periodo: "2025" }, true).periodo).toBeUndefined()
    }
  })

  it("mandos_medios no tiene que elegir empresa", () => {
    const form = base({ empresa_id: "", fecha_desde: "2026-04-13", fecha_hasta: "2026-04-19" })
    expect(validateVacacion(form, true).empresa_id).toBeDefined()
    expect(validateVacacion(form, false).empresa_id).toBeUndefined()
  })
})

describe("payloads — a qué tabla va cada uno", () => {
  it("la licencia tomada lleva fechas, tipo y período", () => {
    const form = base({ fecha_desde: "2026-04-13", fecha_hasta: "2026-04-19", tipo: "vacaciones" })
    const p = payloadTomada(form)
    expect(p.fecha_desde).toBe("2026-04-13")
    expect(p.fecha_hasta).toBe("2026-04-19")
    // El período puede diferir del año de las fechas: tomada en 2026, devengada en 2025.
    expect(p.periodo).toBe(2025)
    expect(p.tipo).toBe("vacaciones")
  })

  it("el pendiente NO lleva fechas ni tipo", () => {
    // Para que falle: que payloadPendiente copiara las fechas del form. El backend las
    // rechazaría, pero el punto es que el front no las mande: son otra entidad.
    const form = base({ pendiente: true, dias_pendientes: "10", fecha_desde: "2026-04-13" })
    const p = payloadPendiente(form) as unknown as Record<string, unknown>
    expect(p.fecha_desde).toBeUndefined()
    expect(p.fecha_hasta).toBeUndefined()
    expect(p.tipo).toBeUndefined()
    expect(p.dias).toBe(10)
    expect(p.periodo).toBe(2025)
  })

  it("el tilde Liquidada liquida TODOS los días, en los dos casos", () => {
    // dias_liquidados es un entero (admite parcial) pero la UI lo maneja binario: tildado =
    // todos. Se compara contra los días DERIVADOS del form, no contra un número escrito acá,
    // así que un cálculo de días roto también rompe esta aserción.
    const tomada = base({ fecha_desde: "2026-04-13", fecha_hasta: "2026-04-19", liquidada: true })
    expect(payloadTomada(tomada).dias_liquidados).toBe(diasDelForm(tomada))

    const pendiente = base({ pendiente: true, dias_pendientes: "10", liquidada: true })
    expect(payloadPendiente(pendiente).dias_liquidados).toBe(diasDelForm(pendiente))
  })

  it("sin tildar Liquidada no se liquida nada", () => {
    const tomada = base({ fecha_desde: "2026-04-13", fecha_hasta: "2026-04-19", liquidada: false })
    expect(payloadTomada(tomada).dias_liquidados).toBe(0)
    expect(payloadPendiente(base({ pendiente: true, dias_pendientes: "10" })).dias_liquidados).toBe(0)
  })
})
