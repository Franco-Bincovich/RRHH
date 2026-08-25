/**
 * El vocabulario de la confirmación de guardado.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR? Se espía el `toast` real
 * (`vi.mock` sobre sonner) y se afirma el STRING que le llega, no que se lo haya llamado: con un
 * `expect(toast.success).toHaveBeenCalled()` el test pasaría aunque el mensaje dijera "undefined
 * creadoa", que es exactamente lo que la concordancia de género puede romper.
 */
import { describe, expect, it, vi } from "vitest"

const mensajes: string[] = []
vi.mock("sonner", () => ({ toast: { success: (m: string) => { mensajes.push(m) } } }))

const { avisarGuardado, avisarHecho } = await import("@/components/features/shared/avisoGuardado")

function ultimo(fn: () => void): string {
  mensajes.length = 0
  fn()
  return mensajes[0] ?? ""
}

describe("el participio concuerda con el género", () => {
  it("femenino: Área creada / actualizada", () => {
    expect(ultimo(() => avisarGuardado("Área", "f", false))).toBe("Área creada")
    expect(ultimo(() => avisarGuardado("Área", "f", true))).toBe("Área actualizada")
  })

  it("masculino: Cliente creado / actualizado", () => {
    expect(ultimo(() => avisarGuardado("Cliente", "m", false))).toBe("Cliente creado")
    expect(ultimo(() => avisarGuardado("Cliente", "m", true))).toBe("Cliente actualizado")
  })

  it("el alta y la edición NO dicen lo mismo", () => {
    // Contestan preguntas distintas, y en un modal que hace las dos cosas el usuario necesita
    // saber cuál pasó — sobre todo cuando abrió el de editar creyendo que era el de crear.
    const alta = ultimo(() => avisarGuardado("Objetivo", "m", false))
    const edicion = ultimo(() => avisarGuardado("Objetivo", "m", true))
    expect(alta).not.toBe(edicion)
  })
})

describe("los actos que no son altas dicen lo que pasó", () => {
  it("avisarHecho pasa el mensaje tal cual", () => {
    expect(ultimo(() => avisarHecho("Onboarding iniciado"))).toBe("Onboarding iniciado")
  })
})
