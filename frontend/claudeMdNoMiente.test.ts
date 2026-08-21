import { execFileSync } from "node:child_process"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"

import { describe, expect, it } from "vitest"

/**
 * 🔴 BARRIDO ESTRUCTURAL — la mitad de front de "CLAUDE.md no puede mentir".
 *
 * El hermano de este barrido vive en `backend/tests/test_claude_md_no_miente.py` y ancla todo
 * lo que se mide leyendo el árbol de archivos, incluida la cantidad de ARCHIVOS de test del
 * front. Lo que aquél no puede medir es el TOTAL DE TESTS del front: no sale de contar `it(`
 * —`it.each` sobre un array de 30 elementos son 30 tests, no uno— sino de colectarlos de
 * verdad. Solo vitest sabe ese número, así que ese ancla vive acá.
 *
 * Es el número que más se pudrió: CLAUDE.md decía **746 tests en 63 archivos** cuando eran
 * **889 en 73**, y lo decía en DOS lugares distintos del documento a la vez.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
 *   · El total se mide corriendo `vitest list`, que COLECTA sin ejecutar. No es una constante
 *     escrita acá: si lo fuera, este archivo sería una segunda copia de la mentira.
 *   · Si la frase de CLAUDE.md no se encuentra, falla por eso — no saltea. "Cero coincidencias"
 *     y "cero problemas" no pueden escribirse igual.
 *   · `vitest list` no ejecuta cuerpos de test, así que no hay recursión; aun así se pasa
 *     RRHH_VITEST_LIST=1 al hijo y el ancla se saltea si ya está puesta. Cinturón y tiradores.
 *
 * 🔴 EL HIJO SE LANZA CON `process.execPath` Y EL `.mjs`, NO CON `node_modules/.bin/vitest`.
 * En Windows ese "binario" es un script de shell sin extensión: `execFileSync` lo intenta
 * ejecutar directo y devuelve **ENOENT**, así que este barrido —el que existe para que los
 * números no mientan— estaba ROJO en la Lenovo y verde en la Mac, sin que cambiara una línea del
 * código auditado. Es exactamente el mismo modo de falla que ya había pagado
 * `services/barridoFront.test.ts` con el separador de paths, y la regla que deja es la misma:
 * **un test que lanza un proceso usa el ejecutable de node que ya está corriendo, nunca un
 * lanzador de `.bin/`.**
 */

const RAIZ = resolve(__dirname, "..")
const CLAUDE_MD = readFileSync(resolve(RAIZ, "CLAUDE.md"), "utf-8")

/** Todos los valores que CLAUDE.md afirma para "N tests en M archivos". */
function declarados(grupo: 1 | 2): number[] {
  return [...CLAUDE_MD.matchAll(/(\d+) tests en (\d+) archivos/g)].map((m) => Number(m[grupo]))
}

/** El total real: se colectan los tests, no se ejecutan. */
function totalReal(): number {
  const salida = execFileSync(process.execPath, [resolve(RAIZ, "frontend/node_modules/vitest/vitest.mjs"), "list"], {
    cwd: resolve(RAIZ, "frontend"),
    encoding: "utf-8",
    env: { ...process.env, RRHH_VITEST_LIST: "1" },
    maxBuffer: 32 * 1024 * 1024,
  })
  return salida.split("\n").filter((l) => l.trim().length > 0).length
}

// Tolerancia: una sesión de front agrega entre 20 y 50 tests, y exigir igualdad exacta
// convertiría esto en un peaje de cada commit — que es como se muere un control. La brecha
// real que lo motivó (746 vs 889 = 143) rojea por casi cinco veces este margen.
const TOLERANCIA = 30

describe("CLAUDE.md no miente sobre la suite del front", () => {
  it("la afirmación sigue estando", () => {
    expect(
      declarados(1).length,
      "No encontré en CLAUDE.md ninguna frase con la forma «N tests en M archivos». " +
        "Si la reescribiste, actualizá el patrón de este barrido en la MISMA sesión: un ancla " +
        "que no matchea es un control apagado, no un control que pasa.",
    ).toBeGreaterThan(0)
  })

  it("el documento no se contradice a sí mismo", () => {
    // Está escrito en dos lugares (la sección de build y la de tests). Si divergen, la próxima
    // sesión corrige uno y deja el otro, que es exactamente lo que ya pasó.
    expect(new Set(declarados(1)).size, `totales distintos: ${declarados(1)}`).toBe(1)
    expect(new Set(declarados(2)).size, `archivos distintos: ${declarados(2)}`).toBe(1)
  })

  it("el total declarado es el real", () => {
    if (process.env.RRHH_VITEST_LIST) return // corriendo dentro de la colecta del hijo
    const real = totalReal()
    const dicho = declarados(1)[0]
    expect(
      Math.abs(dicho - real),
      `CLAUDE.md dice ${dicho} tests de front y vitest colecta ${real}. Corregilo en CLAUDE.md.`,
    ).toBeLessThanOrEqual(TOLERANCIA)
  })
})
