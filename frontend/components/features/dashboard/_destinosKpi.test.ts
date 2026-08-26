import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

import { RUTAS_OCULTAS } from "@/components/layout/nav-config"
import { seccionDeRuta } from "@/services/permisos"
import type { UserRol } from "@/types/auth"
import { DESTINOS, SIN_DESTINO, destino } from "./_destinosKpi"

/**
 * BARRIDO ESTRUCTURAL — a dónde lleva cada KPI del dashboard y quién puede llegar.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. 🔴 **El rol con el que se prueba el gate es `mandos_medios`, no `admin_rrhh`.** Los dos roles
 *    que ven este dashboard —admin y gerencia— pueden LEER todo, así que con cualquiera de ellos
 *    el chequeo de permiso devuelve `true` diez de diez veces y borrarlo entero dejaría el
 *    archivo en verde. `mandos_medios` sólo lee VACACIONES y AUSENCIAS, o sea que parte el
 *    conjunto en dos: es el único rol con el que esto puede desmentir algo.
 * 2. 🔴 **Cada aserción de "no linkea" lleva su CONTRASTE de "sí linkea" con el MISMO rol.** Sin
 *    eso, una función que devolviera siempre `undefined` pasaría la mitad del archivo.
 * 3. **Los títulos se descubren LEYENDO `_kpisDashboard.ts`**, no de una lista escrita acá ni de
 *    un fixture de datos: un KPI nuevo entra al barrido solo, y si le falta el destino hay que
 *    declararlo. Se enmascaran los comentarios antes de buscar —molde `pantallasPublicas`—
 *    porque ese archivo NOMBRA cards en prosa para explicar decisiones, y un barrido por texto
 *    plano las contaría como si fueran cards.
 * 4. **El caso de la querystring se prueba con un rol que NO puede leer esa sección.** Es lo
 *    único que hace que el `split("?")` importe: si se lo saca, `seccionDeRuta` no reconoce
 *    "empleados?estado=activo", devuelve `null` —que el AuthGuard lee como "ruta no gateada"— y
 *    la card linkearía igual. Con `admin_rrhh` ese bug pasa inadvertido: el link sale de todos modos.
 */

const MANDO: UserRol = "mandos_medios"

/** Reemplaza el contenido de los comentarios por espacios, conservando los saltos de línea. */
function sinComentarios(src: string): string {
  const texto = src.replace(/\r\n/g, "\n")
  let salida = ""
  let i = 0
  while (i < texto.length) {
    if (texto.startsWith("/*", i)) {
      const fin = texto.indexOf("*/", i + 2)
      const corte = fin < 0 ? texto.length : fin + 2
      salida += texto.slice(i, corte).replace(/[^\n]/g, " ")
      i = corte
    } else if (texto.startsWith("//", i)) {
      const fin = texto.indexOf("\n", i)
      const corte = fin < 0 ? texto.length : fin
      salida += " ".repeat(corte - i)
      i = corte
    } else {
      salida += texto[i]
      i++
    }
  }
  return salida
}

const FUENTE = sinComentarios(readFileSync(join(__dirname, "_kpisDashboard.ts"), "utf-8"))

/** Los títulos tal como los declara la pantalla: `title: "..."` fuera de los comentarios. */
const TITULOS = [...FUENTE.matchAll(/title:\s*"([^"]+)"/g)].map((m) => m[1])

/** Las cards cuyo destino cayó en `RUTAS_OCULTAS`. Se DERIVA, no se escribe: el día que Franco
 *  reponga /costos, este conjunto queda vacío y el bloque de abajo lo dice en vez de romperse. */
const OCULTAS = Object.keys(DESTINOS)
  .filter((t) => RUTAS_OCULTAS.includes(DESTINOS[t].split("?")[0]))

describe("el mapa cubre las diez cards, en las dos direcciones", () => {
  it("guarda: hay cards que barrer, y el enmascarado no se comió el archivo", () => {
    expect(TITULOS.length).toBeGreaterThanOrEqual(10)
    // Contracara: sin esto, un `sinComentarios` que devolviera "" dejaría TITULOS en [] y todas
    // las comparaciones de abajo se cumplirían por vacío.
    expect(sinComentarios('const t = { title: "X" }')).toContain('title: "X"')
    expect(sinComentarios('/* title: "Fantasma" */')).not.toContain("Fantasma")
  })

  it("todo KPI tiene destino o está declarado SIN destino, con su razón", () => {
    const huerfanos = TITULOS.filter((t) => !(t in DESTINOS) && !(t in SIN_DESTINO))
    expect(huerfanos, "declaralo en DESTINOS o en SIN_DESTINO con el porqué").toEqual([])
    Object.values(SIN_DESTINO).forEach((razon) => expect(razon.length).toBeGreaterThan(40))
  })

  it("y ninguna clave de las dos listas apunta a una card que ya no existe", () => {
    const muertas = [...Object.keys(DESTINOS), ...Object.keys(SIN_DESTINO)]
      .filter((t) => !TITULOS.includes(t))
    expect(muertas, "una entrada muerta esconde al próximo KPI sin destino").toEqual([])
  })

  it("ninguna card está en las dos listas a la vez", () => {
    expect(Object.keys(DESTINOS).filter((t) => t in SIN_DESTINO)).toEqual([])
  })
})

describe("toda ruta destino está gateada por una sección conocida", () => {
  it("ninguna cae en `null`, que el AuthGuard lee como 'pasá'", () => {
    const rutas = Object.values(DESTINOS)
    expect(rutas.length).toBeGreaterThanOrEqual(9) // guarda: sin rutas el forEach no mira nada
    rutas.forEach((ruta) => {
      expect(seccionDeRuta(ruta.split("?")[0]), `sin sección: ${ruta}`).not.toBeNull()
    })
  })
})

describe("una card sin permiso no linkea", () => {
  it("mandos_medios no llega al padrón", () => {
    expect(destino(MANDO, "Colaboradores activos")).toBeUndefined()
  })

  it("EL CONTRASTE: el MISMO rol sí llega a ausencias, que es lo único que lee", () => {
    expect(destino(MANDO, "Ausencias en curso")).toBe("/ausencias")
  })

  it("y no llega a ninguna de las otras", () => {
    expect(TITULOS.filter((t) => destino(MANDO, t) !== undefined)).toEqual(["Ausencias en curso"])
  })

  it("sin rol resuelto no linkea nada (fail-closed)", () => {
    expect(TITULOS.filter((t) => destino(null, t) !== undefined)).toEqual([])
  })

  it("EL CONTRASTE: admin_rrhh llega a todas las que tienen destino y no están ocultas", () => {
    const conLink = TITULOS.filter((t) => destino("admin_rrhh", t) !== undefined)
    expect(conLink).toHaveLength(Object.keys(DESTINOS).length - OCULTAS.length)
  })
})

describe("una card cuya sección salió del menú tampoco linkea", () => {
  /**
   * Es la SEGUNDA punta del ocultamiento de `RUTAS_OCULTAS` (la primera es el sidebar, cubierta
   * por nav-config.test.ts). Va acá y no allá porque el modo de falla es propio de este archivo:
   * la card sigue en `DESTINOS` —a propósito, para que reponer la sección devuelva el link sin
   * tocar nada— así que sin este bloque el filtro se podría borrar y todo quedaría en verde,
   * con el dashboard llevando a una pantalla que el menú esconde.
   *
   * 🚨 El rol es `admin_rrhh`: con cualquier rol que NO pueda leer costos, la card ya no linkea
   * por el gate de permiso y el filtro de ocultamiento no se estaría probando.
   */
  it("guarda: hay al menos una card apuntando a una ruta oculta", () => {
    // Si no la hubiera, todo este bloque pasaría en el vacío. El día que no quede ninguna, se
    // borra el bloque; no se lo deja mirando un conjunto vacío.
    expect(OCULTAS.length).toBeGreaterThanOrEqual(1)
  })

  it.each(OCULTAS)("%s no linkea ni para admin_rrhh", (title) => {
    expect(destino("admin_rrhh", title)).toBeUndefined()
  })

  it("EL CONTRASTE: la MISMA card volvería a linkear si su ruta no estuviera oculta", () => {
    // Sin esto, un `destino()` que devolviera siempre undefined pasaría el bloque entero.
    OCULTAS.forEach((t) => expect(DESTINOS[t]).toBeTruthy())
    const visibles = Object.keys(DESTINOS).filter((t) => !OCULTAS.includes(t))
    expect(visibles.length).toBeGreaterThanOrEqual(1)
    visibles.forEach((t) => expect(destino("admin_rrhh", t), t).toBeTruthy())
  })
})

describe("la querystring no puede saltear el gate", () => {
  it("el filtro viaja en la ruta y la sección se resuelve igual", () => {
    // Si `destino` dejara de cortar por "?", `seccionDeRuta` no reconocería la ruta, devolvería
    // null y ESTE valor saldría con link para mandos_medios. Es la mutación que este test caza.
    expect(DESTINOS["Colaboradores activos"]).toContain("?")
    expect(destino(MANDO, "Colaboradores activos")).toBeUndefined()
    expect(destino("gerencia_lectura", "Colaboradores activos")).toBe("/empleados?estado=activo")
  })
})
