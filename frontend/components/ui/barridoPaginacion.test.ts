import { readdirSync, readFileSync } from "node:fs"
import { dirname, join, resolve, sep } from "node:path"

import { describe, expect, it } from "vitest"

/**
 * 🔴 BARRIDO ESTRUCTURAL — **toda pantalla que pinta `<Table patron="datos">` sobre datos que
 * llegaron con `total` monta `<Pagination>`.**
 *
 * POR QUÉ ESTE EJE Y NO EL OBVIO. La pregunta natural es "quién pide páginas al backend y no
 * dibuja la barra", y ese barrido **nace con excepciones y suma una por cada control nuevo**: un
 * combobox de empleados, un selector de clientes y un buscador de áreas piden `page_size` sin ser
 * listados, así que hay que declararlos uno por uno para siempre. Preguntado al revés —**quién
 * RENDERIZA la tabla de datos**— un selector no entra nunca, porque un selector no dibuja esa
 * tabla. Medido sobre el árbol real al escribirlo: 27 tablas `patron="datos"`, **una sola
 * excepción**, y es la que este repo ya documenta como el único listado que no pagina.
 *
 * EL BUG QUE CIERRA. Una tabla que muestra la primera página sin barra de paginación **no se ve
 * rota**: se ve como un listado corto. El usuario lee 20 filas de 300, exporta creyendo que
 * exporta lo que ve, y no tiene con qué darse cuenta. Es el hermano del bug de `HorasTab` que
 * cubre `paginacionTotales.test.ts` (el total salía de un `.reduce()` sobre la página): ahí el
 * número miente, acá **faltan las filas y no miente nadie**.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
 *   · El descubrimiento es por lectura del árbol Y por el grafo de imports: no hay lista escrita
 *     a mano ni de tablas ni de pantallas. Una pantalla nueva entra sola.
 *   · Verificado en las dos direcciones al escribirlo: se sacó el `<Pagination>` de
 *     `app/(dashboard)/areas/page.tsx` y rojeó **nombrando a `AreasTabla` y a su pantalla**; se
 *     restauró y volvió a verde. Se sacó la excepción de objetivos y rojeó también.
 *   · Las guardas de mínimo corren ANTES de comparar: si el recorrido o el grafo se rompieran,
 *     cada unidad quedaría en un solo archivo, nadie leería `total` y "no hay infractores"
 *     pasaría **sin haber mirado una sola pantalla**. Es el falso verde que este repo ya pagó con
 *     `barridoFront.test.ts`, que en Windows descubría 0 exports y pasaba en verde.
 *
 * 🔑 LOS COMENTARIOS SE ENMASCARAN, y sin eso el barrido no sirve para nada: **cinco pantallas
 * (empresas, equipo, clientes, usuarios, assessment) explican EN PROSA que ahí no hay un `total`
 * del backend**, y un barrido por texto plano las marcaría a las cinco. La salida obvia de ese
 * falso positivo es borrar la explicación — el barrido terminaría destruyendo justo la
 * documentación de la decisión que lo hace correcto. Hay un test abajo que fija que la prosa no
 * cuenta.
 *
 * 🚩 LO QUE NO CUBRE: una pantalla que reciba una respuesta paginada y **no lea `total`** —por
 * ejemplo, contando con `items.length`— no entra en el barrido. Ese es el otro bug (el contador
 * que miente) y lo cubre `paginacionTotales.test.ts` del lado de los que ya paginan. Los tres
 * listados de hoy que traen `total` en la respuesta y cuentan con `.length` son clientes,
 * usuarios y empresas, y los tres declaran por escrito que su backend devuelve el conjunto
 * entero; el día que alguno pagine de verdad, este barrido lo caza al leer `total`.
 */

const RAIZ = resolve(__dirname, "..", "..")
const CARPETAS = ["app", "components"]

/**
 * Excepciones declaradas CON su razón completa y CON su disparador de salida. La contracara de
 * abajo las mata solas cuando el motivo desaparece.
 */
const EXCEPCIONES: Record<string, string> = {
  "components/features/objetivos/ListView.tsx":
    "El tablero de objetivos NO PAGINA, y no le falta la barra: el backend devuelve el árbol " +
    "ENTERO (`objetivo_repo.find_all` es la única lista del sistema sin `.range()`), así que no " +
    "hay páginas que recorrer. Y su `total` no es el número de filas: cuenta las RAÍCES, " +
    "mientras la tabla aplana raíces + subobjetivos y casi siempre muestra más renglones — una " +
    "`<Pagination>` armada con ese total calcularía páginas sobre un número que no es el de la " +
    "tabla. El contrato del wrapper se respeta igual: el pie sale de `total`, nunca de " +
    "`objetivos.length`. DISPARADOR DE SALIDA: cuando el listado de objetivos pagine de verdad " +
    "(hoy lo bloquea que el repo no exponga conteo y que el tope se cuente sobre el árbol " +
    "aplanado), esta entrada se borra en la MISMA sesión y el barrido lo exige. El `<Pagination>` " +
    "que aparece DENTRO de ListView.tsx está en un comentario que explica esto mismo, y el " +
    "barrido lo ignora porque enmascara comentarios: se queda ahí. Descomentarlo sin paginar el " +
    "backend deja el pie mintiendo, que es lo que el aviso del kanban ya cubre.",
}

/**
 * El código sin comentarios, **conservando los saltos de línea** para que las líneas del mensaje
 * de error sigan siendo las del archivo real.
 *
 * 🔴 NORMALIZA CRLF ANTES DE NADA, Y NO ES COSMÉTICO: los archivos del repo están con finales
 * CRLF en Windows, y un `//.*$` sobre una línea terminada en `\r` no matchea nunca — verde en la
 * Mac, rojo en la Lenovo, con el mismo código auditado. La lección está escrita también en
 * `paginacionTotales.test.ts`.
 *
 * ⚠️ No es un parser: no entiende un `//` adentro de un string. Alcanza para lo que se busca acá
 * —un atributo JSX y un identificador— y el test "la prosa no cuenta" fija que un cambio que
 * rompa esta función se vea.
 *
 * ⚠️ Es la copia número 26 de esta función en el front (25 archivos de test la definen, con dos
 * variantes: la que conserva los saltos y la que los colapsa). Unificarla es una tanda propia
 * —toca 25 archivos— y está reportada; acá se eligió la variante que conserva los saltos porque
 * el mensaje de error de este barrido nombra archivos, no líneas, pero el próximo que lo lea no
 * tiene por qué saberlo.
 */
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

/**
 * Rutas relativas a la raíz del front, SIEMPRE con `/` de separador — la normalización vive acá,
 * el único lugar donde nacen las rutas (regla de `barridoSelect.test.ts`).
 *
 * Los archivos de test quedan afuera **y es la línea que impide el falso verde más grande de
 * todos**: cada pantalla tiene su archivo de patrón, esos archivos importan la tabla y varios
 * escriben la barra de paginación en sus aserciones. Si entraran al grafo, cada unidad tendría su
 * paginación "montada" por su propio test y el barrido no podría marcar a nadie.
 */
function archivosDe(carpeta: string): string[] {
  const salida: string[] = []
  const recorrer = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (e.name === "node_modules" || e.name.startsWith(".")) continue
      const p = join(dir, e.name)
      if (e.isDirectory()) recorrer(p)
      else if (!e.name.includes(".test.") && (e.name.endsWith(".tsx") || e.name.endsWith(".ts"))) {
        salida.push(p.slice(RAIZ.length + 1).split(sep).join("/"))
      }
    }
  }
  recorrer(join(RAIZ, carpeta))
  return salida
}

const ARCHIVOS = CARPETAS.flatMap(archivosDe)
const EXISTE = new Set(ARCHIVOS)
const CODIGO = new Map(ARCHIVOS.map((f) => [f, sinComentarios(readFileSync(join(RAIZ, f), "utf-8"))]))
const codigo = (f: string) => CODIGO.get(f) ?? ""

/** Un import del repo → su ruta, o `null` si apunta afuera (node_modules, `@/types`, `@/lib`…). */
function destino(desde: string, spec: string): string | null {
  let base: string
  if (spec.startsWith("@/")) base = spec.slice(2)
  else if (spec.startsWith(".")) base = resolve("/" + dirname(desde), spec).slice(1).split(sep).join("/")
  else return null
  for (const c of [`${base}.tsx`, `${base}.ts`, `${base}/index.tsx`, `${base}/index.ts`]) {
    if (EXISTE.has(c)) return c
  }
  return null
}

const IMPORTADORES = new Map<string, Set<string>>()
for (const f of ARCHIVOS) {
  for (const m of codigo(f).matchAll(/from\s+"([^"]+)"/g)) {
    const t = destino(f, m[1])
    if (!t) continue
    if (!IMPORTADORES.has(t)) IMPORTADORES.set(t, new Set())
    IMPORTADORES.get(t)!.add(f)
  }
}

/**
 * La UNIDAD DE PANTALLA de una tabla: ella misma más todos sus importadores, transitivamente.
 *
 * 🔴 Tiene que ser transitiva y no de un nivel: la tabla vive en `components/features/x/XTable`,
 * el estado en un tab intermedio y la barra en `app/(dashboard)/x/page.tsx`. Mirando un solo
 * salto, inventario y capacitaciones darían infractores siendo correctos.
 */
function unidad(archivo: string): string[] {
  const vistos = new Set([archivo])
  const cola = [archivo]
  while (cola.length > 0) {
    for (const padre of IMPORTADORES.get(cola.pop()!) ?? []) {
      if (!vistos.has(padre)) {
        vistos.add(padre)
        cola.push(padre)
      }
    }
  }
  return [...vistos]
}

/** Las tablas de datos: el atributo JSX, ya sin comentarios. */
const TABLAS = ARCHIVOS.filter((f) => codigo(f).includes('patron="datos"'))

/** Un `total` PELADO: `total_pages`, `tareas_total` y `totalGrupo` no matchean (`_` es \w). */
const leeTotal = (f: string) => /\btotal\b/.test(codigo(f))
const montaPaginacion = (f: string) => /<Pagination\b/.test(codigo(f))

interface Caso {
  tabla: string
  conTotal: string[]
  conPaginacion: string[]
}

const CASOS: Caso[] = TABLAS.map((tabla) => {
  const u = unidad(tabla)
  return { tabla, conTotal: u.filter(leeTotal), conPaginacion: u.filter(montaPaginacion) }
})
const CON_TOTAL = CASOS.filter((c) => c.conTotal.length > 0)
const INFRACTORES = CON_TOTAL.filter(
  (c) => c.conPaginacion.length === 0 && !(c.tabla in EXCEPCIONES),
)

describe("Barrido: una tabla de datos con total lleva su paginación", () => {
  it("el barrido miró de verdad: hay árbol, hay tablas y hay pantallas que sí paginan", () => {
    // Las tres guardas van juntas y en este orden porque tapan tres roturas distintas: el
    // recorrido del árbol, el reconocimiento de la tabla y el grafo de imports. La tercera es la
    // única que puede ver un grafo roto: sin él, ninguna unidad pasa de un archivo.
    expect(ARCHIVOS.length, "el recorrido del árbol no encontró casi nada").toBeGreaterThanOrEqual(300)
    expect(TABLAS.length, "no se reconoció ninguna tabla de datos").toBeGreaterThanOrEqual(20)
    expect(
      CON_TOTAL.filter((c) => c.conPaginacion.length > 0).length,
      "ninguna unidad quedó con `total` Y su barra de paginación: el grafo de imports no está " +
        "uniendo la tabla con su pantalla, así que el barrido no puede marcar a nadie",
    ).toBeGreaterThanOrEqual(12)
  })

  it("ninguna tabla de datos con total se queda sin su barra de paginación", () => {
    expect(
      INFRACTORES.map((c) => `${c.tabla} (lee total en: ${c.conTotal.join(", ")})`),
      "Esta pantalla pinta una tabla `patron=\"datos\"` sobre datos que traen `total` y no monta " +
        "la barra de paginación: el usuario ve la primera página y no tiene cómo saber que hay " +
        "más. Montala donde vive el estado (`page`/`setPage`), o —si esa lista de verdad no " +
        "pagina— declarala en EXCEPCIONES con su razón COMPLETA y su disparador de salida.",
    ).toEqual([])
  })

  it("cada excepción sigue siendo una excepción (si pagina o desaparece, se borra)", () => {
    // La contracara, y es la mitad que hace valer la lista: sin esto una excepción sobrevive a su
    // propio motivo y queda como permiso abierto sobre una pantalla que ya no lo necesita.
    expect(Object.keys(EXCEPCIONES).length).toBeGreaterThanOrEqual(1)
    for (const [archivo, razon] of Object.entries(EXCEPCIONES)) {
      expect(EXISTE.has(archivo), `la excepción apunta a un archivo que no existe: ${archivo}`).toBe(true)
      const caso = CASOS.find((c) => c.tabla === archivo)
      expect(caso, `${archivo} ya no pinta una tabla de datos: sacá su entrada. ${razon}`).toBeDefined()
      expect(caso!.conTotal.length, `${archivo} ya no lee \`total\`: sacá su entrada. ${razon}`)
        .toBeGreaterThan(0)
      expect(
        caso!.conPaginacion,
        `${archivo} YA MONTA la barra de paginación: borrá su entrada de EXCEPCIONES en esta ` +
          `misma sesión. ${razon}`,
      ).toEqual([])
    }
  })

  it("la prosa no cuenta: un `total` que sólo aparece en un comentario no exige paginación", () => {
    // Las cinco pantallas que explican por escrito que ahí no hay `total` del backend. Si el
    // enmascarado se rompiera, las cinco aparecerían como infractoras y el arreglo "natural"
    // sería borrarles la explicación.
    const PROSA = [
      "app/(dashboard)/empresas/page.tsx",
      "app/(dashboard)/equipo/page.tsx",
      "app/(dashboard)/clientes/page.tsx",
      "app/(dashboard)/usuarios/page.tsx",
      "app/(dashboard)/assessment/page.tsx",
    ]
    for (const f of PROSA) {
      expect(EXISTE.has(f), `${f} se movió: actualizá la lista de esta comprobación`).toBe(true)
      expect(readFileSync(join(RAIZ, f), "utf-8"), `${f} ya no menciona \`total\` en prosa`)
        .toMatch(/\btotal\b/)
      expect(leeTotal(f), `${f} pasó a leer \`total\` de verdad, no en un comentario`).toBe(false)
    }
    expect(INFRACTORES.map((c) => c.tabla)).toEqual([])
  })
})
