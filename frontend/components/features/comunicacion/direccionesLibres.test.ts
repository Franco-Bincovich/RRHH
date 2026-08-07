import { describe, expect, it } from "vitest"

import {
  direccionesInvalidas, emailValido, parsearDirecciones,
} from "./direccionesLibres"

/**
 * Parseo y validación de las direcciones escritas a mano, del lado del front.
 *
 * ⚠️ ESTO NO ES LA FRONTERA y el archivo no pretende serlo: la validación que decide corre en el
 * backend (`tests/test_envio_libre.py`), porque el endpoint se puede llamar sin la pantalla. Lo
 * de acá existe para deshabilitar el botón antes de apretarlo.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. Cada regla se prueba en sus DOS lados: direcciones válidas Y rotas, con separador Y sin,
 *    con duplicados Y sin. Con un solo lado, un validador que acepte todo (o que rechace todo)
 *    pasaría — y las dos regresiones son reales: la primera manda mails a la nada, la segunda
 *    deja la feature inusable.
 * 2. Los casos "rotos" son los que un humano escribe de verdad (`ana@`, `ana@k`, `ana k.com`),
 *    no cadenas inventadas. Un test contra `"###"` no dice nada sobre el uso real.
 * 3. `parsearDirecciones` se prueba con los TRES separadores que acepta. Si alguien recorta el
 *    regex a solo comas, el caso del salto de línea rojea — y ese es justo el que sale de pegar
 *    una columna de Excel.
 */

describe("emailValido ataja el typo, no certifica direcciones exóticas", () => {
  it.each(["ana@k.com", "ana.gomez@karstec.com.ar", "ana+rrhh@k.io", "a@b.co"])(
    "acepta %s", (dir) => expect(emailValido(dir)).toBe(true))

  it.each(["ana@", "@k.com", "ana k.com", "ana@k", "ana.k.com", "", "   "])(
    "rechaza %s", (dir) => expect(emailValido(dir)).toBe(false))

  it("ignora los espacios de los bordes (es lo que deja un copiar y pegar)", () => {
    expect(emailValido("  ana@k.com  ")).toBe(true)
  })
})

describe("parsearDirecciones acepta lo que la gente pega de verdad", () => {
  it("separadas por coma", () => {
    expect(parsearDirecciones("ana@k.com, beto@k.com")).toEqual(["ana@k.com", "beto@k.com"])
  })

  it("separadas por salto de línea (una columna de Excel)", () => {
    expect(parsearDirecciones("ana@k.com\nbeto@k.com")).toEqual(["ana@k.com", "beto@k.com"])
  })

  it("separadas por punto y coma", () => {
    expect(parsearDirecciones("ana@k.com;beto@k.com")).toEqual(["ana@k.com", "beto@k.com"])
  })

  it("mezclando separadores y con espacios de más", () => {
    expect(parsearDirecciones(" ana@k.com ,\n beto@k.com ;  cari@k.com "))
      .toEqual(["ana@k.com", "beto@k.com", "cari@k.com"])
  })

  it("una coma al final no genera una dirección vacía", () => {
    expect(parsearDirecciones("ana@k.com,")).toEqual(["ana@k.com"])
  })

  it("texto vacío da lista vacía, no [''] ", () => {
    expect(parsearDirecciones("")).toEqual([])
    expect(parsearDirecciones("   \n  ")).toEqual([])
  })

  it("🔴 deduplica sin distinguir mayúsculas, conservando la primera forma escrita", () => {
    // Mandar dos mails idénticos a alguien de afuera no se puede deshacer.
    expect(parsearDirecciones("Ana@K.com, ana@k.com, ANA@K.COM")).toEqual(["Ana@K.com"])
  })

  it("no deduplica direcciones distintas (si no, mandaría a menos gente de la pedida)", () => {
    expect(parsearDirecciones("ana@k.com, ana2@k.com")).toHaveLength(2)
  })
})

describe("direccionesInvalidas separa el grano de la paja", () => {
  it("🔴 devuelve SOLO las rotas, para poder decir cuáles son", () => {
    expect(direccionesInvalidas(["ana@k.com", "rota@", "beto@k.com", "otra"]))
      .toEqual(["rota@", "otra"])
  })

  it("con todas bien devuelve [] (si no, nunca se habilitaría el envío)", () => {
    expect(direccionesInvalidas(["ana@k.com", "beto@k.com"])).toEqual([])
  })

  it("lista vacía devuelve []", () => {
    expect(direccionesInvalidas([])).toEqual([])
  })
})
