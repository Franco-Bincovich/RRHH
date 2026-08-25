/**
 * 🔴 BARRIDO ESTRUCTURAL — ningún control del producto queda por debajo del mínimo táctil de 44px
 * en pantalla chica.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * LO QUE LO MOTIVÓ, MEDIDO
 * ═══════════════════════════════════════════════════════════════════════════════════
 * **97 controles por debajo de 44px, en 8 pantallas** (25/8/2026). El reparto explica por qué se
 * arregla en los primitivos y no pantalla por pantalla:
 *   · Los de ENCABEZADO ya median 44 — pero porque **cada uno traía su `min-h-11` escrito a
 *     mano**, o sea que el que se olvidara quedaba chico y nadie se enteraba.
 *   · Los de FILA median 32, y su clase estaba **copiada literal en 9 archivos** como
 *     `const ACCION_CLASS`, en dos variantes.
 *   · "Ver detalle" de /auditoria median **24**, el control más chico del producto — y es el
 *     único acceso al detalle en la pantalla donde el detalle ES el contenido.
 *
 * Es el mismo modo de falla que los 81 `<select>` con 29 constantes de estilo copiadas y los 44
 * mensajes por campo con tres tamaños: cuando la medida vive en el consumidor, el arreglo llega a
 * uno solo.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * LA REGLA: 44px HASTA `md`, EL TAMAÑO DEL DISEÑO DE `md` PARA ARRIBA
 * ═══════════════════════════════════════════════════════════════════════════════════
 * La escribió primero `components/ui/select.tsx` (`h-11 md:h-[30px]`) y ahora la comparten
 * `button.tsx`, `AccionFila.tsx` y las dos clases sueltas `PISO_TACTIL` / `PISO_TACTIL_ICONO`.
 * El corte es por ANCHO DE PANTALLA y no por dispositivo: abajo de `md` es donde se usa con el
 * dedo. **Y no agranda la caja en desktop**, que es la otra mitad del requisito — la densidad de
 * §3 (filas de 46px, selectores de 30px) queda intacta.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * EL EJE: UN `<button>` QUE DECIDE SU PROPIA CAJA, NO "TODO `<button>`"
 * ═══════════════════════════════════════════════════════════════════════════════════
 * Se marca el `<button>` crudo (fuera de `components/ui/`) que declara una ALTURA explícita
 * chica: `h-*` / `size-*` / `min-h-*` menores a 11, o un `py-` de 2 o menos. Preguntar por "todo
 * `<button>`" marcaría también a los que no fijan altura —links de texto, disparadores que se
 * estiran con su contenido— cuya caja la decide el contexto y no ellos.
 *
 * Medido al escribirlo: **11 botones en 8 archivos** entraban al barrido, y los 8 archivos son
 * los mismos 8 que el smoke reportó. Los once quedaron con piso; la lista de excepciones nació
 * vacía y conviene que siga así.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR? Las guardas de mínimo corren antes
 * de comparar. Verificado por mutación: sacándole el `PISO_TACTIL` a `SemanaSection`, rojea
 * nombrándolo; y sacándole el `h-11` a `button.tsx`, rojea el test del primitivo.
 */
import { readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"

import { describe, expect, it } from "vitest"

const RAIZ = join(__dirname, "..", "..")

/** Una caja chica declarada a mano: alto/lado menor a 11 (44px), o un padding vertical mínimo. */
const CAJA_CHICA = /\b(?:min-)?(?:h|size)-(?:[0-9]|10|\[[^\]]*\])\b|\bpy-(?:0|0\.5|1|1\.5|2)\b/
/** El piso, en cualquiera de sus formas: la clase directa o una de las constantes compartidas. */
const TIENE_PISO = /\bmin-h-11\b|\b(?:h|size)-11\b|PISO_TACTIL/

/** Controles crudos sin piso, con su razón. Nació VACÍA y conviene que siga así. */
const SIN_PISO: Record<string, string> = {}

function archivosDe(dir: string): string[] {
  const out: string[] = []
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) out.push(...archivosDe(p))
    else out.push(p)
  }
  return out
}

/**
 * Los `<button>` crudos de `components/features/` y `app/`, con su etiqueta de apertura.
 *
 * ⚠️ NO se enmascaran comentarios acá y no hace falta: lo que se busca es la etiqueta `<button`
 * seguida de sus atributos, y un comentario que hable de botones no la contiene.
 */
function aperturasDeBoton(archivo: string): string[] {
  const src = readFileSync(archivo, "utf8")
  const out: string[] = []
  let i = 0
  for (;;) {
    const k = src.indexOf("<button", i)
    if (k === -1) break
    const fin = src.indexOf(">", k)
    out.push(src.slice(k, fin + 1))
    i = fin + 1
  }
  return out
}

const CRUDOS = archivosDe(join(RAIZ, "components"))
  .concat(archivosDe(join(RAIZ, "app")))
  .filter((f) => f.endsWith(".tsx") && !f.includes(".test."))
  // `components/ui/` es donde VIVE la regla: los primitivos declaran la caja a propósito.
  .filter((f) => !f.split(/[\\/]/).includes("ui"))

describe("el barrido está mirando algo", () => {
  it("barre el árbol entero", () => {
    expect(CRUDOS.length).toBeGreaterThanOrEqual(250)
  })

  it("encuentra botones crudos para mirar", () => {
    const conBotones = CRUDOS.filter((f) => aperturasDeBoton(f).length > 0)
    expect(conBotones.length).toBeGreaterThanOrEqual(20)
  })
})

describe("los primitivos llevan la regla, y la llevan los tres", () => {
  it("el botón mide 44px abajo de md y el tamaño del diseño arriba", () => {
    const src = readFileSync(join(RAIZ, "components", "ui", "button.tsx"), "utf8")
    // Las OCHO variantes de tamaño, no una: el bug era justamente que unas sí y otras no.
    for (const par of ["h-11 md:h-8", "h-11 md:h-6", "h-11 md:h-7", "h-11 md:h-9",
                       "size-11 md:size-8", "size-11 md:size-6", "size-11 md:size-7",
                       "size-11 md:size-9"]) {
      expect(src, `button.tsx perdió el par "${par}"`).toContain(par)
    }
  })

  it("el select ya la tenía, y sigue teniéndola", () => {
    const src = readFileSync(join(RAIZ, "components", "ui", "select.tsx"), "utf8")
    expect(src).toContain("h-11 px-2.5 md:h-[30px]")
    expect(src).toContain("h-11 px-3 md:h-[34px]")
  })

  it("la acción de fila mide 44px abajo de md y 32 arriba", () => {
    const src = readFileSync(join(RAIZ, "components", "ui", "AccionFila.tsx"), "utf8")
    expect(src).toContain("size-11 shrink-0 items-center justify-center rounded-md md:size-8")
    expect(src).toContain("h-11 shrink-0 items-center rounded-md px-2 text-xs md:h-7")
    // El desktop NO se agranda: si alguna variante perdiera su `md:`, la densidad de §3 se rompe.
    expect(src).toContain('export const PISO_TACTIL = "min-h-11 md:min-h-0"')
  })
})

describe("ningún control crudo queda por debajo del mínimo táctil", () => {
  it("todo <button> con caja propia declara el piso de 44px", () => {
    const chicos = CRUDOS
      .filter((f) => aperturasDeBoton(f).some((a) => !TIENE_PISO.test(a) && CAJA_CHICA.test(a)))
      .map((f) => f.split(/[\\/]/).pop() as string)
      .filter((n) => !(n in SIN_PISO))
    expect(chicos,
      "Estos botones fijan una caja menor a 44px sin piso táctil: en un teléfono no se pueden " +
      "apretar sin errarle. Usá `<Button>`, `<AccionFila>`, o —si el control es otra cosa— " +
      "`PISO_TACTIL`/`PISO_TACTIL_ICONO` de `components/ui/AccionFila.tsx`.",
    ).toEqual([])
  })

  it("nadie reimplementa la caja de la acción de fila", () => {
    /**
     * La mitad de reimplementación, misma forma que `barridoSelect` y `barridoTarjetas`: la clase
     * estaba copiada literal en 9 archivos como `const ACCION_CLASS`. Un décimo la copiaría igual
     * y quedaría fuera del alcance del primitivo.
     */
    const copias = CRUDOS
      .filter((f) => readFileSync(f, "utf8").includes("const ACCION_CLASS"))
      .map((f) => f.split(/[\\/]/).pop() as string)
    expect(copias,
      "La caja de una acción de fila la decide `components/ui/AccionFila.tsx`. Copiarla en el " +
      "consumidor la saca del alcance del primitivo — es de donde salieron las 9 copias.",
    ).toEqual([])
  })

  it("toda excepción declarada sigue existiendo y tiene razón escrita", () => {
    const nombres = new Set(CRUDOS.map((f) => f.split(/[\\/]/).pop() as string))
    expect(Object.keys(SIN_PISO).filter((n) => !nombres.has(n))).toEqual([])
    expect(Object.entries(SIN_PISO).filter(([, v]) => v.trim().length < 30).map(([k]) => k))
      .toEqual([])
  })
})
