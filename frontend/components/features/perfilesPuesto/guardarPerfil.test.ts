import { beforeEach, describe, expect, it, vi } from "vitest"

const { createPerfil, updatePerfil } = vi.hoisted(() => ({
  createPerfil: vi.fn(), updatePerfil: vi.fn(),
}))
vi.mock("@/services/perfilesPuesto", () => ({ createPerfil, updatePerfil }))

import { ApiError } from "@/services/api"
import type { CampoPerfil, PerfilPuesto } from "@/types/perfilPuesto"

import { guardarPerfil, mensajeDeError, validarPerfil } from "./guardarPerfil"

/**
 * (c) el nombre duplicado muestra el 409 CON SU MENSAJE, no uno genérico.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * · El fake de `createPerfil` distingue los TRES desenlaces que importan (OK · `ApiError` con
 *   mensaje · error pelado) y cada uno tiene su aserción. Con un fake que siempre resuelva, el
 *   caso que de verdad se encuentra operando no podría aparecer nunca.
 * · Se compara contra EL MENSAJE COMPLETO del backend, no contra un `toContain("existe")`: la
 *   forma en que esto se rompe es que alguien lo reemplace por un genérico, y un genérico pasa
 *   cualquier aserción parcial. **La segunda mitad del mensaje es la que importa** —"los perfiles
 *   son de todo el grupo, así que el nombre tiene que ser único en el sistema entero, no por
 *   empresa"— porque es la que explica algo que contradice cómo funciona el resto del producto.
 * · El caso "error pelado" es la contracara: sin él, un `toast(e.message)` sin el `instanceof`
 *   pasaría igual y le mostraría a Capital Humano un "Failed to fetch".
 * · Y se verifica que `guardarPerfil` NO se trague la excepción: si la atrapara y devolviera
 *   `null`, el modal cerraría como si hubiera guardado y el 409 no se vería nunca.
 */

/** El literal del backend, copiado de `schemas/_perfil_puesto_campos.MSG_NOMBRE_DUPLICADO`. */
const MSG_409 =
  "Ya existe un perfil de puesto con ese nombre. Los perfiles son de todo el grupo, así que " +
  "el nombre tiene que ser único en el sistema entero, no por empresa."

const GENERICO = "No se pudo guardar. Intentá de nuevo."

const CAMPOS: CampoPerfil[] = [
  { campo: "nombre", label: "Nombre del perfil", ayuda: "x", tipo: "texto" },
  { campo: "descripcion", label: "Descripción", ayuda: "x", tipo: "textarea" },
]

beforeEach(() => {
  createPerfil.mockReset().mockResolvedValue({ id: "p-1" })
  updatePerfil.mockReset().mockResolvedValue({ id: "p-1" })
})

describe("(c) el 409 de nombre duplicado se muestra tal cual", () => {
  it("conserva el mensaje ENTERO del backend, con la parte que explica por qué", () => {
    expect(mensajeDeError(new ApiError(MSG_409, "PERFIL_DUPLICADO", 409))).toBe(MSG_409)
  })

  it("y no lo reemplaza por el genérico", () => {
    expect(mensajeDeError(new ApiError(MSG_409, "PERFIL_DUPLICADO", 409))).not.toBe(GENERICO)
  })

  it("el 422 de nombre requerido también sale con su texto: es el otro error de negocio", () => {
    const msg = "El nombre del perfil es obligatorio."
    expect(mensajeDeError(new ApiError(msg, "NOMBRE_REQUERIDO", 422))).toBe(msg)
  })

  it("lo que NO es un ApiError sí cae al genérico: un 'Failed to fetch' no le dice nada a nadie", () => {
    expect(mensajeDeError(new Error("Failed to fetch"))).toBe(GENERICO)
    expect(mensajeDeError("algo")).toBe(GENERICO)
  })

  it("🔴 `guardarPerfil` DEJA PASAR la excepción en vez de tragársela", async () => {
    // Si la atrapara y devolviera null, el modal cerraría como si hubiera guardado: el perfil no
    // existiría y el usuario no se enteraría hasta volver a la pantalla.
    createPerfil.mockRejectedValue(new ApiError(MSG_409, "PERFIL_DUPLICADO", 409))
    await expect(guardarPerfil({ nombre: "Analista SQL" }, CAMPOS)).rejects.toThrow(MSG_409)
  })
})

describe("la validación local, antes de mandar", () => {
  it("un nombre en blanco no sale a la red", async () => {
    // El backend también lo rechaza (422 NOMBRE_REQUERIDO), pero pedirle a la red que valide un
    // campo vacío es un viaje que el formulario puede evitar.
    const errs = await guardarPerfil({ nombre: "   " }, CAMPOS)
    expect(errs).toEqual({ nombre: "El nombre del perfil es requerido" })
    expect(createPerfil).not.toHaveBeenCalled()
  })

  it("solo se valida el nombre: los otros campos son opcionales a propósito", () => {
    // Exigirlos llenos enseñaría a escribir cualquier cosa para pasar el validador — es la
    // decisión que el backend ya dejó escrita en `_perfil_puesto_campos.py`.
    expect(validarPerfil({ nombre: "Analista SQL" })).toEqual({})
  })

  it("un nombre de más de 120 tampoco sale: el tope es de producto y el backend lo repite", () => {
    expect(validarPerfil({ nombre: "x".repeat(121) })).toHaveProperty("nombre")
  })
})

describe("alta y edición usan el camino que corresponde", () => {
  it("sin perfil, es un alta", async () => {
    expect(await guardarPerfil({ nombre: " Analista SQL " }, CAMPOS)).toBeNull()
    expect(createPerfil).toHaveBeenCalledWith({ nombre: "Analista SQL", descripcion: "" })
    expect(updatePerfil).not.toHaveBeenCalled()
  })

  it("con perfil, es una edición sobre SU id", async () => {
    const perfil = { id: "p-9", nombre: "Viejo" } as PerfilPuesto
    expect(await guardarPerfil({ nombre: "Nuevo", descripcion: "d" }, CAMPOS, perfil)).toBeNull()
    expect(updatePerfil).toHaveBeenCalledWith("p-9", { nombre: "Nuevo", descripcion: "d" })
    expect(createPerfil).not.toHaveBeenCalled()
  })
})
