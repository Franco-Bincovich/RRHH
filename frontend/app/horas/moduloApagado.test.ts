/**
 * `/horas` con el módulo APAGADO: qué se le dice a quien entra.
 *
 * 🔴 EL CASO REAL, MEDIDO CONTRA EL BACKEND. Con `HORAS_PUBLICO_ENABLED=false` —el default, y el
 * estado de producción hoy— `POST /api/horas-publico/identificar` sale por el AuthMiddleware con
 * **401 `MISSING_TOKEN`**, byte por byte igual que `/api/una-ruta-que-no-existe`. Pero la página
 * de Next se sigue sirviendo, así que un empleado puede entrar y tipear su DNI. Lo que veía era
 * "No autorizado" más la ayuda que dice *"puede que tu usuario todavía no esté habilitado"*: lo
 * mandaba a llamar a Capital Humano por un problema de su legajo que no existe.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR? El padrón de errores tiene
 * los DOS 401 del flujo con codes distintos —`MISSING_TOKEN` e `IDENTIFICACION_INVALIDA`—, que es
 * lo único que puede desmentir una implementación que decida por `status`. Con un solo 401, "mira
 * el code" y "mira el status" darían el mismo verde.
 */
import { describe, expect, it } from "vitest"

import { ApiError } from "@/services/api"
import {
  AYUDA_IDENTIFICACION, MENSAJE_MODULO_APAGADO, esModuloApagado, mensajeDeError,
} from "@/components/features/horasPublico/logica"

const MODULO_APAGADO = new ApiError("No autorizado", "MISSING_TOKEN", 401)
const DNI_RECHAZADO = new ApiError(
  "No pudimos identificarte con ese número.", "IDENTIFICACION_INVALIDA", 401)

describe("el módulo apagado no se confunde con un DNI mal tipeado", () => {
  it("se decide por el CODE, no por el status: los dos rechazos son 401", () => {
    expect(esModuloApagado(MODULO_APAGADO)).toBe(true)
    expect(esModuloApagado(DNI_RECHAZADO)).toBe(false)
  })

  it("con el módulo apagado el mensaje NO culpa al documento", () => {
    const texto = mensajeDeError(MODULO_APAGADO)
    expect(texto).toBe(MENSAJE_MODULO_APAGADO)
    expect(texto).toContain("no está habilitada")
    // La frase que el usuario leía antes: le echaba la culpa a su legajo.
    expect(texto).not.toContain("tu usuario todavía no esté habilitado")
    expect(texto).not.toBe("No autorizado")
  })

  it("con el DNI rechazado sigue saliendo el mensaje del backend, tal cual", () => {
    // El rechazo ÚNICO de la identificación no se toca: es lo que evita el oráculo de DNIs.
    expect(mensajeDeError(DNI_RECHAZADO)).toBe("No pudimos identificarte con ese número.")
  })

  it("la ayuda que menciona el legajo sigue existiendo para el caso que sí la necesita", () => {
    // No se borró: con el módulo ENCENDIDO, un empleado real cuya empresa no tiene clientes
    // cargados recibe el rechazo único y ésa es la única acción que le sirve.
    expect(AYUDA_IDENTIFICACION).toContain("Capital Humano")
  })
})
