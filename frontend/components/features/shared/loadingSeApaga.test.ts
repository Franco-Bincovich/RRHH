import { readdirSync, readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

import { describe, expect, it } from "vitest"

/**
 * BARRIDO ESTRUCTURAL — todo estado de carga que se PRENDE tiene que apagarse en un `finally`.
 *
 * La pantalla de proyectos estuvo caída en producción: el `finally { setLoading(false) }` se
 * perdió al dividir la página y quedó en skeleton para siempre, con el endpoint respondiendo
 * 200. Pasó una división de componentes y 214 tests sin que nadie lo notara, porque ningún test
 * del front mira esa clase de falla: vitest corre sin jsdom, los efectos no se ejecutan, y un
 * render a string muestra el skeleton inicial tanto con el bug como sin él.
 *
 * Barre TODO el front por descubrimiento, nunca contra una lista escrita a mano, así que la
 * próxima pantalla queda cubierta sin tocar este archivo. Acepta los dos idiomas que el repo
 * usa de verdad: `try/finally` y `.finally(() => ...)` sobre la promesa.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
 *
 * Que un archivo prenda un loading y no lo apague — que es lo que pasaba, y por eso el test se
 * escribió contra un rojo real antes de arreglar nada. La guarda de mínimo cubre el otro modo
 * de falla: si el descubrimiento se rompe, el barrido devolvería 0 archivos y pasaría en el
 * vacío, afirmando "todo bien" sin haber mirado nada.
 *
 * ⚠️ LÍMITE, para no venderlo de más: verifica la FORMA del código, no su comportamiento. Un
 * `finally` que apague el loading equivocado pasa igual. Cubre la clase "alguien borró el
 * apagado", que es la que se llevó puesta una pantalla entera; el comportamiento de una carga
 * concreta se prueba aparte (ver `cargarProyectos.test.ts`).
 */

const RAIZ = fileURLToPath(new URL("../../../", import.meta.url))
const CARPETAS = ["app", "components", "hooks"]

/** Nombres de setter que significan "estoy cargando". No incluye setSaving ni setUploading: */
/* esos gobiernan un botón, no la pantalla, y su clase de falla es otra. */
const PRENDE = /\b(set[A-Za-z]*(?:Loading|Cargando))\(true\)/g

function fuentes(dir: string): string[] {
  const salida: string[] = []
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) {
      if (e.name !== "node_modules") salida.push(...fuentes(p))
    } else if (/\.tsx?$/.test(e.name) && !/\.test\.tsx?$/.test(e.name)) {
      salida.push(p)
    }
  }
  return salida
}

/** Un par = un archivo y un setter de carga que ese archivo prende. */
const PARES: { archivo: string; setter: string; src: string }[] = []
for (const carpeta of CARPETAS) {
  for (const archivo of fuentes(join(RAIZ, carpeta))) {
    const src = readFileSync(archivo, "utf8")
    const setters = new Set([...src.matchAll(PRENDE)].map((m) => m[1]))
    for (const setter of setters) {
      PARES.push({ archivo: archivo.slice(RAIZ.length), setter, src })
    }
  }
}

function loApaga(src: string, setter: string): boolean {
  return new RegExp(`finally[\\s\\S]{0,200}?\\b${setter}\\(false\\)`).test(src)
}

describe("todo loading que se prende se apaga en un finally", () => {
  it("el barrido encontró algo que mirar", () => {
    // Sin esta guarda, romper `fuentes` o el regex daría 0 pares y el test pasaría en el vacío.
    expect(PARES.length).toBeGreaterThanOrEqual(55)
  })

  it.each(PARES.map((p) => [p.archivo, p.setter, p.src] as const))(
    "%s apaga %s",
    (_archivo, setter, src) => {
      expect(loApaga(src, setter)).toBe(true)
    },
  )

  it("el propio detector distingue el caso roto del sano", () => {
    // Si `loApaga` devolviera true siempre, los 61 casos de arriba pasarían sin comprobar nada.
    const sano = "setLoading(true); try { a() } finally { setLoading(false) }"
    const sanoPromesa = "setLoading(true); pedir().then(x).finally(() => setLoading(false))"
    const roto = "setLoading(true); try { a() } catch { b() }"
    const apagaAdentroDelTry = "setLoading(true); try { a(); setLoading(false) } catch { b() }"

    expect(loApaga(sano, "setLoading")).toBe(true)
    expect(loApaga(sanoPromesa, "setLoading")).toBe(true)
    expect(loApaga(roto, "setLoading")).toBe(false)
    expect(loApaga(apagaAdentroDelTry, "setLoading")).toBe(false)
  })
})
