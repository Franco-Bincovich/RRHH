import { describe, expect, it } from "vitest"

import { ApiError } from "@/services/api"
import {
  AYUDA_IDENTIFICACION, DIAS_HACIA_ATRAS, FORM_HORAS_VACIO, FORM_LICENCIA_VACIO, MAX_HORAS_DIA,
  bodyHoras, bodyLicencia, esSesionMuerta, mensajeDeError, normalizarDni, puedeEnviar,
  validarHoras, validarLicencia, ventanaFechas,
} from "@/components/features/horasPublico/logica"

/**
 * Toda la lógica de la pantalla pública. Es lo ÚNICO que se puede probar de verdad sin jsdom.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS FALLEN?
 *
 * **1. Habría que probar UN solo caso por función.** Con un solo input, "valida" y "acepta todo"
 * son indistinguibles. Cada validador se prueba con el caso completo Y con cada obligatorio
 * faltando por separado, y `esSesionMuerta`/`mensajeDeError` con los DOS desenlaces.
 *
 * **2. `esSesionMuerta` habría que probarlo con un solo 401.** Los DOS rechazos del flujo son
 * 401 (`SESION_INVALIDA` e `IDENTIFICACION_INVALIDA`), así que se pasan los dos: si la función
 * mirara el status en vez del code, el segundo la delataría — y ese bug borraría una sesión sana
 * por un dígito mal tipeado.
 *
 * **3. `mensajeDeError` habría que probarlo solo con ApiError.** Se prueban los dos: si
 * devolviera siempre el genérico, el mensaje accionable del backend ("ya tenés 10 horas
 * cargadas...") se perdería y el test no lo vería.
 */

const HOY = new Date("2026-08-20T12:00:00Z")

const HORAS_OK = {
  ...FORM_HORAS_VACIO, fecha: "2026-08-19", horas: "4", modalidad: "home_office",
  cliente_id: "c1",
}
const LICENCIA_OK = { ...FORM_LICENCIA_VACIO, fecha_desde: "2026-08-18", fecha_hasta: "2026-08-19" }

describe("normalizarDni", () => {
  it("saca puntos, guiones y espacios", () => {
    // El usuario tipea el DNI como se lee en el documento; `empleados.dni` está sin separadores.
    // Sin esto, un DNI correcto sale rechazado.
    expect(normalizarDni("12.345.678")).toBe("12345678")
    expect(normalizarDni("12-345-678")).toBe("12345678")
    expect(normalizarDni(" 12 345 678 ")).toBe("12345678")
  })

  it("deja vacío lo que no tiene dígitos", () => {
    expect(normalizarDni("abc")).toBe("")
    expect(normalizarDni("")).toBe("")
  })
})

describe("validarHoras — los cuatro obligatorios", () => {
  it("con todo completo no hay errores", () => {
    expect(validarHoras(HORAS_OK)).toEqual({})
  })

  it.each(["fecha", "horas", "modalidad", "cliente_id"] as const)(
    "sin %s no deja enviar", (campo) => {
      // Uno por uno: si se probaran todos juntos, un validador que solo mire `fecha` pasaría.
      const errs = validarHoras({ ...HORAS_OK, [campo]: "" })
      expect(errs[campo]).toBeTruthy()
      expect(puedeEnviar("horas", { ...HORAS_OK, [campo]: "" }, FORM_LICENCIA_VACIO)).toBe(false)
    },
  )

  it("el formulario vacío tiene los cuatro errores", () => {
    expect(Object.keys(validarHoras(FORM_HORAS_VACIO)).sort())
      .toEqual(["cliente_id", "fecha", "horas", "modalidad"])
  })

  it("rechaza horas fuera de rango y avisa el tope ANTES de mandar", () => {
    expect(validarHoras({ ...HORAS_OK, horas: "0" }).horas).toBeTruthy()
    expect(validarHoras({ ...HORAS_OK, horas: "-2" }).horas).toBeTruthy()
    expect(validarHoras({ ...HORAS_OK, horas: String(MAX_HORAS_DIA + 1) }).horas)
      .toContain(String(MAX_HORAS_DIA))
    expect(validarHoras({ ...HORAS_OK, horas: String(MAX_HORAS_DIA) })).toEqual({})
  })

  it("proyecto, tarea y descripción son OPCIONALES", () => {
    // Es el caso normal del flujo, no el borde.
    expect(validarHoras({ ...HORAS_OK, proyecto_texto: "", tarea_texto: "", descripcion: "" }))
      .toEqual({})
  })
})

describe("validarLicencia", () => {
  it("con desde y hasta alcanza", () => {
    expect(validarLicencia(LICENCIA_OK)).toEqual({})
  })

  it.each(["fecha_desde", "fecha_hasta"] as const)("sin %s no deja enviar", (campo) => {
    expect(validarLicencia({ ...LICENCIA_OK, [campo]: "" })[campo]).toBeTruthy()
  })

  it("rechaza el rango invertido antes de que lo haga el backend", () => {
    expect(validarLicencia({ ...LICENCIA_OK, fecha_desde: "2026-08-19",
                             fecha_hasta: "2026-08-18" }).fecha_hasta).toBeTruthy()
  })

  it("las observaciones son opcionales", () => {
    expect(validarLicencia({ ...LICENCIA_OK, observaciones: "" })).toEqual({})
  })
})

describe("puedeEnviar — el modo decide qué se valida", () => {
  it("en modo licencia NO exige los campos de horas", () => {
    // 🔴 Es la regla "al elegir licencia se desactiva la carga de horas", expresada donde se
    // puede probar. Si `puedeEnviar` validara siempre las horas, elegir licencia dejaría el
    // botón muerto para siempre.
    expect(puedeEnviar("licencia", FORM_HORAS_VACIO, LICENCIA_OK)).toBe(true)
  })

  it("en modo horas NO exige los campos de licencia", () => {
    expect(puedeEnviar("horas", HORAS_OK, FORM_LICENCIA_VACIO)).toBe(true)
  })

  it("con los dos vacíos no deja enviar en ningún modo", () => {
    expect(puedeEnviar("horas", FORM_HORAS_VACIO, FORM_LICENCIA_VACIO)).toBe(false)
    expect(puedeEnviar("licencia", FORM_HORAS_VACIO, FORM_LICENCIA_VACIO)).toBe(false)
  })
})

describe("ventanaFechas", () => {
  it("abre exactamente los 30 días que el backend acepta", () => {
    const { min, max } = ventanaFechas(HOY)
    expect(max).toBe("2026-08-20")
    expect(min).toBe("2026-07-21")           // 20/8 menos 30 días
    expect(DIAS_HACIA_ATRAS).toBe(30)
  })
})

describe("los bodies", () => {
  it("no manda los opcionales vacíos", () => {
    // "" no es un dato: mandarlo guardaría un texto vacío donde el usuario no escribió nada.
    const b = bodyHoras("tok", HORAS_OK, "idem-1")
    expect(b.proyecto_texto).toBeUndefined()
    expect(b.tarea_texto).toBeUndefined()
    expect(b.descripcion).toBeUndefined()
  })

  it("manda los opcionales con contenido, sin espacios de más", () => {
    const b = bodyHoras("tok", { ...HORAS_OK, proyecto_texto: "  Migración  " }, "idem-1")
    expect(b.proyecto_texto).toBe("Migración")
  })

  it("las horas viajan como número y el token y la idempotencia van adentro", () => {
    const b = bodyHoras("tok", HORAS_OK, "idem-1")
    expect(b.horas).toBe(4)
    expect([b.token, b.idempotencia]).toEqual(["tok", "idem-1"])
  })

  it("🔴 el body NO lleva empleado_id ni empresa_id", () => {
    // La identidad sale de la sesión en el backend. Si el front los mandara, adivinar un DNI
    // dejaría de ser el techo del daño.
    const b = bodyHoras("tok", HORAS_OK, "i") as unknown as Record<string, unknown>
    expect(b.empleado_id).toBeUndefined()
    expect(b.empresa_id).toBeUndefined()
    const l = bodyLicencia("tok", LICENCIA_OK) as unknown as Record<string, unknown>
    expect(l.empleado_id).toBeUndefined()
  })

  it("el body de licencia NO lleva campos de horas", () => {
    // Los dos endpoints reciben bodies disjuntos: la regla está en el TIPO, no en un if.
    const l = bodyLicencia("tok", LICENCIA_OK) as unknown as Record<string, unknown>
    for (const k of ["horas", "modalidad", "cliente_id", "proyecto_texto", "tarea_texto"]) {
      expect(l[k]).toBeUndefined()
    }
  })
})

describe("esSesionMuerta — por CODE, nunca por status", () => {
  it("un token vencido mata la sesión", () => {
    expect(esSesionMuerta(new ApiError("Tu sesión expiró.", "SESION_INVALIDA", 401))).toBe(true)
  })

  it("🔴 un DNI rechazado NO mata la sesión, aunque también sea 401", () => {
    // Si mirara el status, este caso borraría una sesión sana por un dígito mal tipeado.
    expect(esSesionMuerta(new ApiError("No pudimos identificarte.",
                                       "IDENTIFICACION_INVALIDA", 401))).toBe(false)
  })

  it("un error de negocio tampoco", () => {
    expect(esSesionMuerta(new ApiError("Ese día ya tenés 10 horas.", "TOPE_HORAS_DIA", 422)))
      .toBe(false)
    expect(esSesionMuerta(new Error("network"))).toBe(false)
  })
})

describe("mensajeDeError — conserva el del backend", () => {
  it("muestra el mensaje accionable tal cual", () => {
    // Reemplazarlo por un genérico tiraría justo lo que el usuario necesita para resolverlo.
    const e = new ApiError("Ese día ya tenés 10 horas cargadas y el máximo es 12. Podés cargar "
                           + "hasta 2 más.", "TOPE_HORAS_DIA", 422)
    expect(mensajeDeError(e)).toContain("hasta 2 más")
  })

  it("usa un genérico solo cuando no es un error de la API", () => {
    expect(mensajeDeError(new Error("network"))).toContain("internet")
    expect(mensajeDeError(undefined)).toContain("internet")
  })
})

describe("la ayuda del rechazo de identificación", () => {
  it("🔴 no nombra ningún motivo, porque el backend usa rechazo único", () => {
    // Hoy hay 0 clientes cargados y eso rechaza a TODO el padrón, pero desde el front se ve
    // igual que un DNI mal tipeado. El texto es CONSTANTE: al no depender de la respuesta no
    // distingue nada, así que no rompe la garantía — y le da al empleado la acción que sí sirve.
    expect(AYUDA_IDENTIFICACION).toContain("Recursos Humanos")
    for (const motivo of ["cliente", "baja", "inactiv", "no existe", "límite"]) {
      expect(AYUDA_IDENTIFICACION.toLowerCase()).not.toContain(motivo)
    }
  })
})
