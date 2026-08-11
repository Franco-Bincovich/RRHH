import { readFileSync } from "node:fs"
import { resolve } from "node:path"

import { describe, expect, it } from "vitest"

/**
 * Contraste WCAG de los pares de tokens del bloque `.dark` de `globals.css`.
 *
 * 🔴 QUÉ **NO** PRUEBA ESTE TEST — leerlo antes de confiar en un verde suyo:
 *
 * **No prueba que el navegador aplique la regla `.dark select option`** de
 * `globals.css:154-158`, ni que el popup de un `<select>` se vea bien. Eso NO se puede
 * verificar acá: vitest corre con `environment: "node"`, sin jsdom y sin motor de layout, así
 * que no hay nada que pueda dibujar un `<option>`. **Esa verificación es visual y la hace una
 * persona**, y encima cambia por plataforma (en macOS el popup del `<select>` fue un menú
 * nativo que ignoraba los estilos de autor durante años).
 *
 * Tampoco prueba que la regla exista. Un test que grepee el archivo buscando el selector solo
 * puede fallar si alguien borra la línea: no dice si funciona, y es exactamente la tautología
 * que la regla transversal del repo descarta ("un test solo prueba lo que el fake puede
 * desmentir").
 *
 * ✅ QUÉ SÍ PRUEBA: que **los tokens sobre los que esa regla se apoya sigan siendo legibles**.
 * La regla no elige colores, los toma prestados (`var(--popover)` / `var(--popover-foreground)`).
 * El día que alguien ajuste la paleta oscura —y va a pasar: `--popover` es un `#1e293b` escrito
 * a mano— el popup puede volverse ilegible sin que se toque una sola línea de la regla. Los
 * valores son entradas reales que cambian solas, así que este test PUEDE fallar por una razón
 * real, y esa es la única razón por la que existe.
 *
 * La fuente son los valores REALES del archivo, parseados del bloque `.dark`. Nunca constantes
 * copiadas acá: un test que replica adentro el dato que dice verificar no puede fallar.
 */

const GLOBALS_CSS = resolve(__dirname, "globals.css")

/** Umbral AA de WCAG 2.1 para texto de tamaño normal. Es el que exige `docs/UX-UI.md:630`. */
const UMBRAL_AA = 4.5

/** Los pares fondo/texto que el tema usa de verdad. */
const PARES: ReadonlyArray<readonly [string, string]> = [
  ["--popover", "--popover-foreground"],
  ["--background", "--foreground"],
  ["--card", "--card-foreground"],
  ["--primary", "--primary-foreground"],
]

/**
 * Pares que HOY no llegan al umbral, declarados con su razón y su ratio medido.
 *
 * Se declaran en vez de sacarse del barrido, por el mismo criterio que
 * `tests/test_paridad_list_export.py` en el backend: un par que desaparece de la lista deja de
 * mirarse para siempre; uno declarado sigue vigilado en LAS DOS direcciones — no puede empeorar,
 * y si mejora el test se pone rojo para que se saque la excepción en vez de quedar de adorno.
 */
const BRECHAS_DECLARADAS: Record<string, { readonly ratio: number; readonly razon: string }> = {
  "--primary/--primary-foreground": {
    ratio: 3.68,
    razon:
      "El botón primario en modo oscuro (#3b82f6 con texto blanco) da 3.68:1. En modo CLARO el " +
      "mismo par da 6.18:1 y cumple: el azul se aclaró para que el botón resaltara contra el " +
      "fondo oscuro de la página, y eso bajó el contraste del texto que va ENCIMA del botón. " +
      "Arreglarlo es una decisión de marca (cambiar --primary oscuro, u oscurecer " +
      "--primary-foreground), no un fix de este test.",
  },
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

function parseColor(valor: string): LinearRgb {
  const v = valor.trim()
  if (v.startsWith("#")) return hexToLinearRgb(v)
  const ok = v.match(/^oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+([\d.]+)/)
  if (ok) {
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

/** Extrae los `--token: valor;` del bloque `.dark { ... }`, no del `:root`: son distintos. */
function tokensDelBloqueDark(css: string): Record<string, string> {
  const bloque = css.match(/\.dark\s*\{([^}]*)\}/)
  if (!bloque) throw new Error("No se encontró el bloque `.dark { ... }` en globals.css")
  const tokens: Record<string, string> = {}
  for (const [, nombre, valor] of bloque[1].matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    tokens[nombre] = valor.trim()
  }
  return tokens
}

describe("Contraste de los tokens del tema oscuro", () => {
  it("cada par fondo/texto del bloque .dark llega a 4.5:1, con la fórmula anclada primero", () => {
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

    // ── 2. LOS PARES REALES ────────────────────────────────────────────────────
    const tokens = tokensDelBloqueDark(readFileSync(GLOBALS_CSS, "utf-8"))
    // Guarda de mínimo: si el parseo se rompiera, `tokens` vendría vacío, cada par tiraría
    // "token ausente" y el barrido pasaría sin haber comparado nada.
    expect(Object.keys(tokens).length).toBeGreaterThanOrEqual(20)

    const medidos: Record<string, number> = {}
    for (const [fondo, texto] of PARES) {
      expect(tokens[fondo], `falta ${fondo} en el bloque .dark`).toBeDefined()
      expect(tokens[texto], `falta ${texto} en el bloque .dark`).toBeDefined()
      medidos[`${fondo}/${texto}`] = ratioContraste(
        parseColor(tokens[fondo]),
        parseColor(tokens[texto]),
      )
    }

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
