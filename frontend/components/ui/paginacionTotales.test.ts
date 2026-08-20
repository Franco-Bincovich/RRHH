import { readdirSync, readFileSync } from "node:fs"
import path from "node:path"

import { describe, expect, it } from "vitest"

/**
 * 🔴 REGLA DEL MOLDE: si una pantalla pagina, sus totales vienen del BACKEND.
 *
 * El bug que esto cierra estaba vivo en `HorasTab`: paginaba de a 20 y armaba el pie con
 * `horas.reduce(...)`, o sea sumaba la PÁGINA y lo mostraba como el total del proyecto. Con 400
 * cargas decía "9 h", y el número cambiaba al pasar de página. No hay error, no hay warning: un
 * total plausible es indistinguible de uno correcto, y el usuario no tiene con qué compararlo.
 *
 * Es la clase de bug que esta tanda de paginación puede REPLICAR CATORCE VECES, una por listado,
 * porque el `.reduce()` es correcto mientras la página sea todo — que es exactamente el estado en
 * el que se escribe y se prueba. Por eso el test barre a TODOS los consumidores de `Pagination` en
 * vez de fijar el caso de HorasTab: los listados que se paginen en las próximas cuatro sesiones
 * quedan cubiertos sin tocar este archivo.
 *
 * 🔑 QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDA FALLAR: que un componente que importa
 * `Pagination` tenga un `.reduce(`. Volver a poner el de HorasTab lo rojea. Y si el
 * descubrimiento se rompiera, la guarda de mínimo lo caza antes de que pase en el vacío.
 *
 * ⚠️ El barrido filtra por `entry.name` y normaliza el separador — nunca compara un tramo de path
 * con `/` literal. Es la regla que dejó `barridoFront.test.ts` después de dar verde en la Mac y
 * rojo en la Lenovo sin que cambiara el código auditado.
 */

const RAIZ = path.resolve(__dirname, "..", "..")
const CARPETAS = ["app", "components"]

/** Excepciones declaradas CON su razón. Vacío hoy: ningún consumidor deriva totales localmente. */
const EXCEPCIONES: Record<string, string> = {}

/**
 * El código sin comentarios.
 *
 * 🔴 HACE FALTA, Y EL PROPIO ARCHIVO AUDITADO LO DEMOSTRÓ: el comentario que explica por qué se
 * sacó el `.reduce()` de HorasTab contiene la palabra `.reduce(`, así que un barrido por texto
 * plano marcaba como culpable justo al archivo que ya estaba arreglado. Es la misma trampa que
 * `test_storage_punto_unico.py` documenta en el backend, y tiene el mismo desenlace peligroso:
 * el "arreglo" natural del falso positivo es borrar la explicación.
 *
 * ⚠️ No es un parser: no entiende strings que contengan `//`. Alcanza para esto —lo que se busca
 * es una llamada a método— y el test de abajo fija que la prosa no cuente, así que un cambio que
 * rompa esta función se ve.
 *
 * 🔴 NORMALIZA CRLF ANTES DE NADA, Y NO ES COSMÉTICO. Los archivos del repo están con finales
 * `\r\n` en Windows: partiendo por `\n` cada línea queda terminada en `\r`, que para el regex de
 * JS es un terminador de línea, así que `//.*$` no matchea NUNCA y la función devolvía el código
 * intacto. Verde en la Mac, rojo en la Lenovo, sin que cambie el código auditado — el mismo modo
 * de falla que dejó `barridoFront.test.ts` documentado en CLAUDE.md.
 */
function sinComentarios(src: string): string {
  return src
    .replace(/\r\n/g, "\n")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n")
    .map((l) => l.replace(/\/\/.*$/, ""))
    .join("\n")
}

function archivosDe(dir: string): string[] {
  const salida: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const completo = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name === ".next") continue
      salida.push(...archivosDe(completo))
    } else if (/\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name)) {
      salida.push(completo)
    }
  }
  return salida
}

const TODOS = CARPETAS.flatMap((c) => archivosDe(path.join(RAIZ, c)))

/** Los que renderizan la barra: importan `Pagination` y lo usan como componente. */
const CONSUMIDORES = TODOS.filter((f) => {
  const src = readFileSync(f, "utf8")
  return src.includes("components/ui/Pagination") && src.includes("<Pagination")
}).map((f) => ({ rel: path.relative(RAIZ, f).split(path.sep).join("/"), src: readFileSync(f, "utf8") }))

describe("totales en pantallas paginadas", () => {
  it("el barrido encuentra los consumidores de Pagination", () => {
    // Guarda contra el falso verde: con 0 consumidores todo lo de abajo pasa sin mirar nada.
    expect(CONSUMIDORES.length).toBeGreaterThanOrEqual(7)
  })

  it("ninguna pantalla paginada deriva un agregado con .reduce()", () => {
    const culpables = CONSUMIDORES
      .filter((c) => sinComentarios(c.src).includes(".reduce("))
      .filter((c) => !(c.rel in EXCEPCIONES))
      .map((c) => c.rel)
    expect(culpables).toEqual([])
  })

  it("🔑 la PROSA no cuenta: un comentario que menciona .reduce( no es una violación", () => {
    // Sin esto, el arreglo natural del falso positivo es borrar la explicación de por qué el
    // `.reduce()` no va — o sea, borrar justo lo que evita que alguien lo reponga.
    const conProsa = "// antes esto hacía horas.reduce((s, h) => s + h.horas, 0)\nconst x = 1"
    expect(sinComentarios(conProsa).includes(".reduce(")).toBe(false)
    // 🔴 El MISMO caso con finales CRLF. Sin la normalización esto pasa a `true` y el barrido
    // entero se vuelve inútil en Windows mientras sigue verde en la Mac.
    expect(sinComentarios(conProsa.replace(/\n/g, "\r\n")).includes(".reduce(")).toBe(false)
    // Y la contracara: el código de verdad SÍ se detecta. Sin esta mitad, una función que
    // devolviera "" pasaría los dos tests.
    expect(sinComentarios("const t = xs.reduce(f, 0)").includes(".reduce(")).toBe(true)
  })

  it("las excepciones declaradas siguen existiendo", () => {
    // Una excepción que apunta a un archivo borrado es ruido que esconde el próximo caso.
    const muertas = Object.keys(EXCEPCIONES).filter(
      (rel) => !CONSUMIDORES.some((c) => c.rel === rel),
    )
    expect(muertas).toEqual([])
  })

  it("🔴 (f) el pie sale de `total`, NUNCA de la cantidad de filas de la página", () => {
    /*
     * El `.reduce()` de arriba caza el agregado derivado; esto caza al hermano que el barrido no
     * veía: pasarle a `<Pagination>` el largo de la página como si fuera el total
     * (`total={items.length}`). Es el MISMO bug de HorasTab por otra puerta y es todavía más
     * invisible, porque mientras el listado entre en una página el número es correcto — el pie
     * dice "Mostrando 1–20 de 20" con 1.042 filas cargadas, la barra muestra una sola página y no
     * hay ningún error. Se ve recién cuando hay datos de verdad, o sea en producción.
     *
     * 🔬 VERIFICADO QUE PUEDE FALLAR: con `total={items.length}` en /empleados este test rojea
     * nombrando el archivo; con `total={total}` pasa.
     */
    const invocaciones = CONSUMIDORES.flatMap((c) =>
      (sinComentarios(c.src).match(/<Pagination[\s\S]*?\/>/g) ?? []).map((jsx) => ({ rel: c.rel, jsx })),
    )
    // Guarda contra el falso verde: si el regex dejara de matchear el JSX, no habría nada que
    // mirar y el test pasaría en el vacío.
    expect(invocaciones.length).toBeGreaterThanOrEqual(7)

    const culpables = invocaciones
      .filter(({ jsx }) => /total=\{[^}]*\.length[^}]*\}/.test(jsx))
      .map(({ rel }) => rel)
    expect(culpables).toEqual([])

    // Contracara: el detector reconoce el bug cuando está. Sin esto, un regex roto pasaría las
    // dos aserciones de arriba.
    expect(/total=\{[^}]*\.length[^}]*\}/.test("<Pagination total={items.length} />")).toBe(true)
    expect(/total=\{[^}]*\.length[^}]*\}/.test("<Pagination total={total} />")).toBe(false)
  })

  it("HorasTab lee los totales de la respuesta y no de la página", () => {
    // El caso concreto que originó la regla, fijado además del barrido: si alguien vuelve a
    // derivarlo, el test de arriba dice "hay un reduce" y este dice qué dejó de leerse.
    const horasTab = CONSUMIDORES.find((c) => c.rel.endsWith("proyectos/HorasTab.tsx"))
    expect(horasTab, "HorasTab dejó de consumir Pagination").toBeDefined()
    expect(horasTab!.src).toContain("total_horas")
    expect(horasTab!.src).toContain("total_costo")
  })
})
