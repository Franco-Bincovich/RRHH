import { readFileSync } from "node:fs"
import { resolve } from "node:path"

import { describe, expect, it } from "vitest"

/**
 * Contraste WCAG de los pares de tokens de la paleta (`app/paleta.css`), en LOS DOS TEMAS.
 *
 * 🔴 QUÉ **NO** PRUEBA ESTE TEST — leerlo antes de confiar en un verde suyo:
 *
 * **No prueba que el navegador aplique la regla `.dark select option`** de `globals.css`, ni que
 * el popup de un `<select>` se vea bien. Eso NO se puede verificar acá: vitest corre con
 * `environment: "node"`, sin jsdom y sin motor de layout, así que no hay nada que pueda dibujar
 * un `<option>`. **Esa verificación es visual y la hace una persona**, y encima cambia por
 * plataforma (en macOS el popup del `<select>` fue un menú nativo que ignoraba los estilos de
 * autor durante años).
 *
 * Tampoco prueba que la regla exista. Un test que grepee el archivo buscando el selector solo
 * puede fallar si alguien borra la línea: no dice si funciona, y es exactamente la tautología
 * que la regla transversal del repo descarta ("un test solo prueba lo que el fake puede
 * desmentir").
 *
 * **Y no mira los colores que se aplican con `style={{...}}` inline.** `utils/colorEmpresa.ts`
 * tiene 26 hex que se pintan inline en las tres componentes del organigrama (`ArbolProyecto.tsx`,
 * `CardsProyecto.tsx`, `ArbolEmpresa.tsx`): el estilo inline gana sobre cualquier clase o
 * variable, así que ningún token los alcanza y este barrido —que solo lee el archivo de la
 * paleta— no los ve. No es una falla del barrido, es su alcance: un color que nace en un `.ts` y
 * viaja por `style={{}}` no pasa por ninguna hoja de estilo. Está anotado en
 * `docs/DEUDA-TECNICA.md` §9.
 *
 * ✅ QUÉ SÍ PRUEBA: que **los tokens sobre los que el tema se apoya sigan siendo legibles**, en
 * modo claro y en modo oscuro. La regla del `<option>`, por ejemplo, no elige colores: los toma
 * prestados (`var(--popover)` / `var(--popover-foreground)`). El día que alguien ajuste la
 * paleta —y pasa: la paleta entera se reemplazó el 19/8/2026 por la de
 * `docs/SISTEMA-DE-DISENO.md`— el popup puede volverse ilegible sin que se toque una sola línea
 * de la regla. Los valores son entradas reales que cambian solas, así que este test PUEDE fallar
 * por una razón real, y esa es la única razón por la que existe.
 *
 * 🔴 **LOS DOS TEMAS, NO UNO.** Hasta el 19/8/2026 este test parseaba únicamente el bloque
 * `.dark` y el `:root` no se leía nunca. Eso dejaba un doble punto ciego que costó caro:
 * `--muted/--muted-foreground` daba **4.34:1 en claro** —por debajo del umbral— y nadie lo
 * miraba, porque era un par que no estaba en `PARES` **y además** vivía en el tema que no se
 * parseaba. Medir un solo tema es medio barrido con la confianza de uno entero. La paleta de
 * Capital Humano lo subió a 5.24:1 el mismo día, pero el agujero era del test y por eso el test
 * es lo primero que se arregló: el par que nadie mira vuelve a fallar sin que nadie se entere.
 *
 * La fuente son los valores REALES del archivo, parseados de cada bloque. Nunca constantes
 * copiadas acá: un test que replica adentro el dato que dice verificar no puede fallar.
 */

/**
 * Los tokens viven en `app/paleta.css`, no en `globals.css`: los dos bloques se mudaron ahí el
 * 19/8/2026 al pasar `globals.css` del límite de 200 líneas. `globals.css` quedó con el cableado
 * (`@theme inline`, capa base, print) y lo importa. Este test apunta al archivo de los VALORES,
 * que es lo único que puede medir.
 */
const PALETA_CSS = resolve(__dirname, "paleta.css")

/** Umbral AA de WCAG 2.1 para texto de tamaño normal. Es el que exige `docs/UX-UI.md:630`. */
const UMBRAL_AA = 4.5

/**
 * Los dos temas del archivo, con el selector CSS del que sale cada uno.
 *
 * El nombre viaja hasta el mensaje de error a propósito: un ratio suelto no dice en qué tema
 * falló, y los dos bloques declaran los MISMOS tokens con valores distintos.
 */
const TEMAS: ReadonlyArray<readonly [string, RegExp]> = [
  ["claro", /:root\s*\{([^}]*)\}/],
  ["oscuro", /\.dark\s*\{([^}]*)\}/],
]

/**
 * Los pares fondo/texto que el tema usa de verdad. Se miden en LOS DOS temas.
 *
 * ⚠️ `--sidebar-accent/--sidebar-accent-foreground` **entró recién con la paleta del 19/8**, y
 * antes no podía estar: su valor en oscuro era `oklch(0.279 0.041 260 / 80%)`, con canal alfa. Un
 * color translúcido no tiene un ratio propio —depende de sobre qué se componga—, y medirlo
 * ignorando el alfa daría un número que se lee como una medición y no lo es. `parseColor` rechaza
 * el alfa en vez de descartarlo en silencio, justamente para que ese caso no pueda entrar
 * disfrazado, y sigue rechazándolo: el día que un token de estos vuelva a llevar alfa, este
 * barrido se pone rojo en vez de inventar un número.
 */
const PARES: ReadonlyArray<readonly [string, string]> = [
  ["--popover", "--popover-foreground"],
  ["--background", "--foreground"],
  ["--card", "--card-foreground"],
  ["--primary", "--primary-foreground"],
  ["--muted", "--muted-foreground"],
  ["--secondary", "--secondary-foreground"],
  ["--accent", "--accent-foreground"],
  ["--sidebar", "--sidebar-foreground"],
  ["--sidebar-primary", "--sidebar-primary-foreground"],
  ["--sidebar-accent", "--sidebar-accent-foreground"],
  /*
   * Los tres pares SEMÁNTICOS. Entraron el 19/8/2026, cuando el chip de estado de /empleados dejó
   * de ser `bg-primary` (relleno azul en cada fila, contra la regla de §3 de que los chips de
   * filtro son el único azul) y pasó a los washes. Hasta entonces la paleta declaraba ocho tokens
   * semánticos que **ningún test miraba**: el archivo los contaba para el piso de tokens y no
   * medía uno solo. El más ajustado es success en claro, 4,73:1.
   */
  ["--success-wash", "--success"],
  ["--warning-wash", "--warning"],
  ["--danger-wash", "--destructive"],
]

/**
 * Piso de tokens por bloque. Medido el 19/8/2026 con la paleta de Capital Humano ya aplicada:
 * `:root` trae 40 y `.dark` 39 (eran 32 y 31 con la paleta anterior; los 8 semánticos nuevos
 * —`--success*`, `--warning*`, `--danger-*`— son la diferencia).
 *
 * El piso es 30 y NO el conteo exacto a propósito: su trabajo es cazar un parseo roto —que
 * devuelve el objeto vacío o un puñado de tokens, y ahí cada par tiraría "token ausente" y el
 * barrido pasaría sin haber comparado nada—, no anclar cuántos tokens tiene la paleta. Un
 * conteo exacto se pondría rojo cada vez que se agrega un token, sin que nada esté mal.
 */
const MINIMO_TOKENS_POR_BLOQUE = 30

/**
 * Pares que HOY no llegan al umbral, declarados con su tema, su razón y su ratio medido.
 *
 * La clave es `tema:fondo/texto` — el mismo par puede cumplir en un tema y fallar en el otro, y
 * de hecho los dos casos de abajo son exactamente eso.
 *
 * Se declaran en vez de sacarse del barrido, por el mismo criterio que
 * `tests/test_paridad_list_export.py` en el backend: un par que desaparece de la lista deja de
 * mirarse para siempre; uno declarado sigue vigilado en LAS DOS direcciones — no puede empeorar,
 * y si mejora el test se pone rojo para que se saque la excepción en vez de quedar de adorno.
 */
const BRECHAS_DECLARADAS: Record<string, { readonly ratio: number; readonly razon: string }> = {
  // 🟢 VACÍO A PROPÓSITO — la paleta de `docs/SISTEMA-DE-DISENO.md` cerró las tres brechas que
  // había el 19/8/2026, y cerrarlas OBLIGA a borrarlas: la verificación de abajo es en las dos
  // direcciones, así que una excepción que ya cumple pone el test en rojo en vez de quedar de
  // adorno. Las tres, para que no se relean como pendientes:
  //   · `oscuro:--primary/--primary-foreground`               3.68:1 → 7.97:1 (el foreground
  //     dejó de ser blanco y pasó al fondo de página #0B1220)
  //   · `oscuro:--sidebar-primary/--sidebar-primary-foreground` 3.68:1 → 7.97:1 (mismo par, la
  //     variable del sidebar; se arreglaron juntas porque comparten valor)
  //   · `claro:--muted/--muted-foreground`                     4.34:1 → 5.24:1
  // El mecanismo queda: la próxima brecha se declara acá con su tema, su ratio medido y su razón,
  // nunca sacando el par de `PARES`.
}

// ─── Conversión de color a luminancia relativa (WCAG 2.1 §relative luminance) ───

/** Un color en sRGB lineal (sin gamma), componentes 0..1 y potencialmente fuera de gama. */
type LinearRgb = readonly [number, number, number]

function hexToLinearRgb(hex: string): LinearRgb {
  const h = hex.replace("#", "")
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h
  const canal = [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16) / 255)
  const lineal = canal.map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return [lineal[0], lineal[1], lineal[2]]
}

/** oklch → sRGB lineal, vía OKLab y la matriz LMS inversa de Björn Ottosson. */
function oklchToLinearRgb(L: number, C: number, H: number): LinearRgb {
  const h = (H * Math.PI) / 180
  const a = C * Math.cos(h)
  const b = C * Math.sin(h)
  const lRaiz = L + 0.3963377774 * a + 0.2158037573 * b
  const mRaiz = L - 0.1055613458 * a - 0.0638541728 * b
  const sRaiz = L - 0.0894841775 * a - 1.291485548 * b
  const l = lRaiz ** 3
  const m = mRaiz ** 3
  const s = sRaiz ** 3
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ]
}

/**
 * Convierte el valor CRUDO de un token a sRGB lineal. Soporta hex y oklch, y **rechaza** todo
 * lo demás en vez de devolver algo.
 *
 * 🔴 Los dos formatos conviven en el archivo y hay que sostener los dos: la paleta anterior
 * escribía las superficies en hex y las neutrales en oklch, y la del 19/8/2026 llegó entera en
 * hex. Un parser de un solo formato no falla ruidosamente: se queda sin poder medir la mitad de
 * los pares, y si eso se resolviera con un `continue` el barrido pasaría en verde midiendo menos
 * de lo que dice. Por eso acá se tira, y por eso el test ancla más abajo un valor de CADA
 * formato antes de medir nada.
 *
 * El alfa se rechaza a propósito: un color translúcido no tiene ratio propio —depende del fondo
 * sobre el que se componga, que el token no declara—, así que medirlo ignorando el canal daría
 * un número inventado con cara de medición.
 */
function parseColor(valor: string): LinearRgb {
  const v = valor.trim()
  if (v.startsWith("#")) {
    if (v.replace("#", "").length === 8 || v.replace("#", "").length === 4) {
      throw new Error(`Color con canal alfa, no se puede medir su contraste: "${valor}"`)
    }
    return hexToLinearRgb(v)
  }
  const ok = v.match(/^oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+([\d.]+)\s*(\/[^)]*)?\)/)
  if (ok) {
    if (ok[4]) throw new Error(`Color con canal alfa, no se puede medir su contraste: "${valor}"`)
    const L = ok[1].endsWith("%") ? parseFloat(ok[1]) / 100 : parseFloat(ok[1])
    return oklchToLinearRgb(L, parseFloat(ok[2]), parseFloat(ok[3]))
  }
  throw new Error(`Formato de color no soportado: "${valor}"`)
}

function luminanciaRelativa(rgb: LinearRgb): number {
  const [r, g, b] = rgb.map((c) => Math.min(1, Math.max(0, c)))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function ratioContraste(a: LinearRgb, b: LinearRgb): number {
  const la = luminanciaRelativa(a)
  const lb = luminanciaRelativa(b)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

// ─── Lectura de los tokens reales ───

/**
 * Extrae los `--token: valor;` del bloque que matchee `selector`.
 *
 * Un bloque por tema: `:root` y `.dark` declaran los MISMOS nombres con valores distintos, así
 * que mezclarlos en un solo diccionario haría que el último pisara al primero y el test mediría
 * un tema dos veces creyendo que midió dos.
 */
function tokensDelBloque(css: string, tema: string, selector: RegExp): Record<string, string> {
  const bloque = css.match(selector)
  if (!bloque) throw new Error(`No se encontró el bloque del tema "${tema}" en paleta.css`)
  const tokens: Record<string, string> = {}
  for (const [, nombre, valor] of bloque[1].matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    tokens[nombre] = valor.trim()
  }
  return tokens
}

describe("Contraste de los tokens de la paleta", () => {
  it("cada par fondo/texto llega a 4.5:1 en los dos temas, con la fórmula anclada primero", () => {
    // ── 1. ANCLAS DE LA FÓRMULA ────────────────────────────────────────────────
    // Van PRIMERO y con valores literales, no leídos del archivo: si la conversión
    // oklch→luminancia estuviera mal, todos los ratios de abajo serían números inventados que
    // pasan siempre. Anclarla con entradas fijas es lo que separa "el token cambió" de "la
    // fórmula está rota" — sin esto, el test entero podría estar midiendo cualquier cosa.
    const NEGRO = hexToLinearRgb("#000000")
    expect(ratioContraste(hexToLinearRgb("#ffffff"), NEGRO)).toBeCloseTo(21, 6)
    // el mismo 21:1 llegando por el otro camino: si oklch estuviera mal, este no daría 21
    expect(ratioContraste(oklchToLinearRgb(1, 0, 0), NEGRO)).toBeCloseTo(21, 4)
    // y un par mixto oklch/hex con resultado conocido y calculado por fuera de este archivo
    expect(ratioContraste(oklchToLinearRgb(0.985, 0, 0), hexToLinearRgb("#1e293b"))).toBeCloseTo(
      14.01,
      2,
    )

    // Los DOS formatos entran por `parseColor`, que es el camino que usan los pares reales: las
    // anclas de arriba llaman a los conversores directo y no probarían que el despacho por
    // formato funciona. Un parser que no reconociera el hex —o el oklch— tiraría acá.
    expect(ratioContraste(parseColor("#ffffff"), parseColor("oklch(0 0 0)"))).toBeCloseTo(21, 4)
    // y el alfa se rechaza, en los dos formatos, en vez de medirse ignorando el canal
    expect(() => parseColor("oklch(0.279 0.041 260 / 80%)")).toThrow(/alfa/)
    expect(() => parseColor("#1e293b80")).toThrow(/alfa/)

    // ── 2. LOS PARES REALES, TEMA POR TEMA ─────────────────────────────────────
    const css = readFileSync(PALETA_CSS, "utf-8")
    const medidos: Record<string, number> = {}

    for (const [tema, selector] of TEMAS) {
      const tokens = tokensDelBloque(css, tema, selector)
      // Guarda de mínimo, por tema: si el parseo de ESTE bloque se rompiera, `tokens` vendría
      // vacío, cada par tiraría "token ausente" y el barrido pasaría sin haber comparado nada.
      // Va por tema y no sobre el total a propósito: un total sano puede esconder un bloque
      // entero en cero si el otro trae el doble.
      expect(
        Object.keys(tokens).length,
        `el bloque del tema "${tema}" trajo ${Object.keys(tokens).length} tokens`,
      ).toBeGreaterThanOrEqual(MINIMO_TOKENS_POR_BLOQUE)

      for (const [fondo, texto] of PARES) {
        expect(tokens[fondo], `falta ${fondo} en el tema ${tema}`).toBeDefined()
        expect(tokens[texto], `falta ${texto} en el tema ${tema}`).toBeDefined()
        medidos[`${tema}:${fondo}/${texto}`] = ratioContraste(
          parseColor(tokens[fondo]),
          parseColor(tokens[texto]),
        )
      }
    }

    // Contracara de la guarda: si `PARES` o `TEMAS` se vaciaran, `medidos` vendría corto y el
    // bucle de abajo no compararía nada.
    expect(Object.keys(medidos).length).toBe(TEMAS.length * PARES.length)

    // Ninguna brecha declarada puede apuntar a un par que ya no se mide: una excepción muerta
    // es ruido que tapa el próximo caso.
    for (const clave of Object.keys(BRECHAS_DECLARADAS)) {
      expect(medidos[clave], `brecha declarada para un par inexistente: ${clave}`).toBeDefined()
    }

    for (const [clave, ratio] of Object.entries(medidos)) {
      const brecha = BRECHAS_DECLARADAS[clave]
      const dice = `${clave} = ${ratio.toFixed(2)}:1`
      if (!brecha) {
        expect(ratio, `${dice} — no llega al mínimo de ${UMBRAL_AA}:1 de docs/UX-UI.md`)
          .toBeGreaterThanOrEqual(UMBRAL_AA)
        continue
      }
      expect(ratio, `${dice} — EMPEORÓ respecto del ${brecha.ratio}:1 declarado. ${brecha.razon}`)
        .toBeGreaterThanOrEqual(brecha.ratio - 0.01)
      expect(ratio, `${dice} — ya supera ${UMBRAL_AA}:1: sacá su entrada de BRECHAS_DECLARADAS`)
        .toBeLessThan(UMBRAL_AA)
    }
  })
})
