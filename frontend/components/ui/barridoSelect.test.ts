import { readdirSync, readFileSync } from "node:fs"
import { join, resolve, sep } from "node:path"

import { describe, expect, it } from "vitest"

/**
 * 🔴 BARRIDO ESTRUCTURAL — **ningún `<select>` nativo fuera de `components/ui/select.tsx`.**
 *
 * POR QUÉ EXISTE. Antes de la migración había **81 `<select>` nativos en 53 archivos**, vestidos
 * con constantes de estilo copiadas de un archivo a otro: `SELECT_CLASS` declarada en 14 archivos
 * con **10 valores distintos**, `SEL` en 9 con 3, `SELECT_CLS` en 3 con 3, más 17 con la clase
 * escrita inline. Ninguna de esas diferencias era una decisión de diseño; eran copias que
 * driftearon hasta que dos selects de la misma pantalla tenían distinto alto y distinto anillo de
 * foco. **Migrarlos no alcanza: sin un barrido, el próximo `<select>` nativo entra en el próximo
 * PR y la divergencia empieza de nuevo desde uno.** Es el mismo criterio que sostiene los
 * barridos del backend — el que impide que una regla dependa de que alguien se acuerde.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
 *   · El descubrimiento es por lectura del árbol: no hay lista escrita a mano de qué mirar. Un
 *     archivo nuevo entra solo. Verificado en las dos direcciones al escribirlo: se agregó un
 *     `<select>` nativo en una pantalla cualquiera y rojeó; se sacó la excepción del primitivo y
 *     rojeó también.
 *   · La guarda de mínimo corre ANTES de comparar. Si el escaneo se rompiera —un `sep` de
 *     Windows, una carpeta renombrada— encontraría 0 archivos y "no hay selects nativos" pasaría
 *     en el vacío, que es exactamente el falso verde que este repo ya pagó una vez
 *     (`barridoFront.test.ts` descubría 0 exports en Windows y pasaba).
 *   · Las excepciones se verifican en las DOS direcciones: que lo que hay esté declarado, y que
 *     lo declarado siga existiendo. Una excepción muerta es ruido que tapa el próximo caso.
 *
 * 🔑 LOS COMENTARIOS SE ENMASCARAN ANTES DE BUSCAR, y no es un detalle: hay **6 lugares del repo
 * que mencionan `<select>` en prosa** para explicar por qué NO se usó uno —los checkboxes de
 * `FiltersBar`, los dos botones de `EnvioModo`, el combobox de empleados, el `<select multiple>`
 * de objetivos, el selector de empresa que la migración 108 borró de `ClienteModal`, y el select
 * encadenado de `CamposAusencia`—. Un barrido por texto plano los marcaría a todos, y la salida
 * obvia sería borrar esos comentarios: el barrido terminaría destruyendo la explicación de las
 * decisiones que documenta. Por eso se enmascara y no se recorta.
 *
 * 🚩 LO QUE NO CUBRE: un `<select>` que se construya con `React.createElement("select", …)` o que
 * llegue desde una librería externa. Ninguno de los dos existe hoy en el repo (verificado), y los
 * dos sobre-pasarían —dejarían pasar uno— nunca al revés: este barrido no puede inventar un
 * incumplimiento.
 */

const RAIZ = resolve(__dirname, "..", "..")
const CARPETAS = ["app", "components"]

/** El primitivo y nada más. La clave se escribe siempre con `/`, como la normaliza `archivosDe`. */
const EXCEPCIONES: Record<string, string> = {
  "components/ui/select.tsx":
    "Es EL primitivo: el único lugar del repo donde el `<select>` nativo se escribe a mano. " +
    "Envuelve al nativo a propósito (en mobile abre el picker del sistema operativo, y el " +
    "teclado y el lector de pantalla funcionan gratis), así que el `<select>` de adentro no es " +
    "una excepción a la regla: es la regla.",
}

/**
 * Devuelve las rutas relativas a la raíz del front, SIEMPRE con `/` como separador.
 *
 * 🔑 La normalización vive acá, que es el único lugar donde nacen las rutas. Es la regla que
 * dejó el falso verde de `barridoFront.test.ts`: armaba los paths con `join` (separador `\` en
 * Windows) y después filtraba comparando contra un `/` literal, así que en la Lenovo descubría
 * cero archivos y pasaba en verde con el mismo código que en la Mac.
 */
function archivosDe(carpeta: string): string[] {
  const salida: string[] = []
  const recorrer = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (e.name === "node_modules" || e.name.startsWith(".")) continue
      const p = join(dir, e.name)
      if (e.isDirectory()) recorrer(p)
      // Los `.test.*` quedan fuera: no pintan pantalla, y este mismo archivo escribe `<select`
      // ocho veces —en el mensaje de error y en la expresión regular— así que sin esta línea el
      // barrido se marca a sí mismo. No se pierde cobertura: lo que se vigila es el producto.
      else if (!e.name.includes(".test.") && (e.name.endsWith(".tsx") || e.name.endsWith(".ts"))) {
        salida.push(p.slice(RAIZ.length + 1).split(sep).join("/"))
      }
    }
  }
  recorrer(join(RAIZ, carpeta))
  return salida
}

/**
 * Reemplaza el CONTENIDO de los comentarios por espacios, conservando los `\n` para que los
 * números de línea del mensaje de error sigan siendo los del archivo real.
 */
function sinComentarios(texto: string): string {
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

/** Todos los `<select` nativos del archivo, con su línea, ya sin comentarios. */
function nativosDe(rel: string): number[] {
  const codigo = sinComentarios(readFileSync(join(RAIZ, rel), "utf-8"))
  const lineas: number[] = []
  for (const m of codigo.matchAll(/<select\b/g)) {
    lineas.push(codigo.slice(0, m.index).split("\n").length)
  }
  return lineas
}

const ARCHIVOS = CARPETAS.flatMap(archivosDe)

describe("Barrido: el <select> nativo vive en un solo archivo", () => {
  it("no hay ningún <select> nativo fuera de components/ui/select.tsx", () => {
    // Guarda de mínimo: si el recorrido se rompiera, `ARCHIVOS` vendría vacío y la aserción de
    // abajo pasaría sin haber abierto un solo archivo.
    expect(ARCHIVOS.length).toBeGreaterThanOrEqual(300)

    const infractores = ARCHIVOS.filter((f) => !(f in EXCEPCIONES) && nativosDe(f).length > 0).map(
      (f) => `${f}:${nativosDe(f).join(",")}`,
    )
    expect(
      infractores,
      "Usá `<Select>` de @/components/ui/select en vez del `<select>` nativo. Tiene los dos " +
        "tamaños del sistema de diseño (sm 30px para filtros, md 34px para formularios), el " +
        "área táctil de 44px en mobile, el foco visible y el estado de error. Si este caso " +
        "necesita de verdad el nativo, declaralo en EXCEPCIONES con su razón.",
    ).toEqual([])
  })

  it("cada excepción declarada sigue teniendo un <select> nativo", () => {
    // La contracara. Sin esto, una excepción sobrevive a la desaparición de su motivo y queda
    // como permiso abierto para un archivo que ya no lo necesita.
    expect(Object.keys(EXCEPCIONES).length).toBeGreaterThanOrEqual(1)
    for (const [archivo, razon] of Object.entries(EXCEPCIONES)) {
      expect(ARCHIVOS, `la excepción apunta a un archivo inexistente: ${archivo}`).toContain(
        archivo,
      )
      expect(
        nativosDe(archivo).length,
        `${archivo} ya no tiene ningún <select> nativo: sacá su entrada de EXCEPCIONES. ${razon}`,
      ).toBeGreaterThan(0)
    }
  })

  it("todo archivo que pinta un <Select> lo importa de @/components/ui/select", () => {
    // La otra mitad de "que no venga de ui/select": el barrido de arriba solo mira el nativo, y
    // un `Select` declarado localmente lo esquivaría entero sin escribir un solo `<select>`.
    const usuarios = ARCHIVOS.filter(
      (f) => f !== "components/ui/select.tsx" && /<Select\b/.test(sinComentarios(readFileSync(join(RAIZ, f), "utf-8"))),
    )
    // Guarda de mínimo: son 53 archivos migrados; si el filtro se rompiera, el bucle no correría.
    expect(usuarios.length).toBeGreaterThanOrEqual(40)

    const sinImport = usuarios.filter(
      (f) => !readFileSync(join(RAIZ, f), "utf-8").includes('from "@/components/ui/select"'),
    )
    expect(
      sinImport,
      "estos archivos usan <Select> sin importarlo del primitivo: o falta el import, o hay un " +
        "Select local que esquiva el barrido del nativo",
    ).toEqual([])
  })
})
