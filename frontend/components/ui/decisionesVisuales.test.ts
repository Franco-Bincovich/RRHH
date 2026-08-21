import { readdirSync, readFileSync } from "node:fs"
import { join, resolve, sep } from "node:path"

import { describe, expect, it } from "vitest"

/**
 * 🔴 BARRIDO ESTRUCTURAL — **las decisiones VISUALES de `docs/SISTEMA-DE-DISENO.md` §2 y §3
 * están en el código, y siguen escritas en el documento.**
 *
 * POR QUÉ EXISTE, con el caso que lo motivó. §2 pide DOS movimientos al apuntar, distintos a
 * propósito: la fila de tabla se DESPLAZA sin elevarse (la elevación rompe la alineación de las
 * columnas) y la tarjeta se ELEVA 3px con el borde iluminado. Sólo se construyó el primero. El
 * segundo llegó a existir como variante `interactive` en `components/ui/card.tsx` y se quedó con
 * **cero consumidores**: las dos tarjetas que sí son un control —el onboarding en curso y el
 * template— tenían cada una su versión a mano (`hover:border-primary/40 hover:shadow-sm`), la
 * mitad del patrón, sin elevación, sin duración declarada y sin nada que avisara que habían
 * divergido del primitivo. `tsc` estaba contento, los 1451 tests estaban verdes y la pantalla no
 * cumplía el documento. **Ninguna otra clase de test de este repo puede ver eso**: los de
 * componente miran el markup de UNA pantalla y no saben qué prometió el sistema de diseño.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR? Verificado en las dos
 * direcciones antes de darlo por bueno:
 *   · Se le sacó `hover:-translate-y-[3px]` a `card.tsx` → rojo, nombrando la decisión y su cita.
 *   · Se le sacó `min-h-[30px]` a `fichaPanel.tsx` —una decisión declarada que SÍ existía— → rojo.
 *   · Se le puso a `PATRON_DATOS` una sombra de elevación → rojo por la prohibición de §2.
 *   · Se cambió una cita para que no aparezca en el documento → rojo por la FUENTE, no por el
 *     código: si §2 se reescribe, este archivo tiene que releerse antes de seguir en verde.
 *
 * 🔑 CADA DECISIÓN CITA SU FUENTE, y la cita se busca en el documento REAL. Eso es lo que impide
 * el modo de falla de este repo: un test que afirma una regla que el documento ya no dice, y que
 * pasa igual porque nadie los comparó. La cita se normaliza en blancos (el documento envuelve a
 * 100 columnas, así que casi todas cruzan un salto de línea).
 *
 * 🚩 LO QUE NO CUBRE, declarado abajo en `NO_VERIFICABLE` con su motivo. Este barrido mira
 * CLASES en los primitivos: puede ver "46px" y "sin elevación", no puede ver "el copy explica
 * por qué no hay datos" ni "la primaria va última". Forzarlo a mirar eso daría aserciones que
 * pasan sin comprobar nada, que es peor que no tenerlas.
 */

const RAIZ = resolve(__dirname, "..", "..")
const REPO = resolve(RAIZ, "..")

/** El documento, con los blancos colapsados: sus párrafos vienen envueltos a 100 columnas. */
const DOC = readFileSync(join(REPO, "docs", "SISTEMA-DE-DISENO.md"), "utf-8").replace(/\s+/g, " ")

interface Decision {
  /** La sección del sistema de diseño de la que sale. */
  seccion: "§2" | "§3"
  /** Literal del documento. Se busca en el documento real, normalizado en blancos. */
  cita: string
  /** Qué decide, en una línea: es lo que se lee cuando el test rojea. */
  que: string
  /** Dónde vive la decisión, relativo a `frontend/`. */
  archivo: string
  /** Lo que ese archivo TIENE que contener para que la decisión esté construida. */
  debe: string[]
  /** Lo que NO puede contener. Una decisión que prohíbe algo se rompe agregando, no sacando. */
  noDebe?: string[]
}

const DECISIONES: Decision[] = [
  // ── §2 · El tratamiento de superficie ────────────────────────────────────────
  {
    seccion: "§2",
    cita: "Tarjetas: elevación de 3px con borde iluminado.",
    que: "la tarjeta que ES un control se eleva 3px y se le ilumina el borde al apuntarla",
    archivo: "components/ui/card.tsx",
    debe: ["hover:-translate-y-[3px]", "hover:border-primary"],
  },
  {
    seccion: "§2",
    cita: "Transiciones de 160ms.",
    que: "los 160ms de la tarjeta, declarados y no heredados del default de Tailwind (150ms)",
    archivo: "components/ui/card.tsx",
    debe: ["duration-[160ms]"],
  },
  {
    seccion: "§2",
    cita: "Tarjetas y filas OPACAS.** Sin transparencia ni desenfoque.",
    que: "la tarjeta es opaca: `bg-card` pleno, sin vidrio y sin fondo traslúcido",
    archivo: "components/ui/card.tsx",
    // El `hover:shadow-md` de `interactive` no es la elevación de base: aparece sólo al apuntar y
    // acompaña al desplazamiento de §2. Lo que esta decisión prohíbe es la superficie traslúcida.
    debe: ["bg-card"],
    noDebe: ["backdrop-blur", "bg-card/"],
  },
  {
    seccion: "§2",
    cita: "desplazamiento de 2–3px, **sin elevación** — en una tabla la elevación rompe la alineación de las columnas",
    que: "la FILA se desplaza y NO se eleva: ni translate-y, ni sombra que no sea la marca interior",
    archivo: "components/ui/tablePatron.ts",
    debe: ["translate-x-[2px]"],
    noDebe: ["translate-y", "shadow-md", "shadow-lg", "shadow-sm", "hover:shadow"],
  },
  {
    seccion: "§2",
    cita: "**Densidad alta.** Filas de 46px.",
    que: "la fila de datos mide 46px",
    archivo: "components/ui/tablePatron.ts",
    debe: ["[&_tbody_tr]:h-[46px]"],
  },
  // ── §3 · Tabla con paginación ────────────────────────────────────────────────
  {
    seccion: "§3",
    cita: "encabezado de 32px en la superficie secundaria con mayúsculas de 10px",
    // `h-8` ES 32px (8 × 4px). Se verifica la clase y no el número: en el código no hay ningún
    // "32" que buscar, y alguien que mida el encabezado y no lo encuentre lo agregaría dos veces.
    que: "el encabezado mide 32px (`h-8`), va sobre `--secondary` y en mayúsculas de 10px",
    archivo: "components/ui/tablePatron.ts",
    debe: [
      "[&_thead_th]:h-8",
      "[&_thead_th]:bg-secondary",
      "[&_thead_th]:text-[10px]",
      "[&_thead_th]:uppercase",
    ],
  },
  {
    seccion: "§3",
    cita: "marca de 3px de `--primary` a la izquierda y desplazamiento de 2px, en 160ms",
    que: "la marca de hover son 3px de `--primary` a la izquierda, en 160ms",
    archivo: "components/ui/tablePatron.ts",
    debe: ["inset_3px_0_0_0_var(--primary)", "duration-[160ms]"],
  },
  // ── §3 · Filtros ─────────────────────────────────────────────────────────────
  {
    seccion: "§3",
    cita: "Los chips usan `--accent` con borde `--primary`",
    que: "el chip de filtro activo: relleno `--accent`, borde `--primary`",
    archivo: "components/ui/FiltrosActivos.tsx",
    debe: ["bg-accent", "border-primary"],
  },
  {
    seccion: "§3",
    cita: "selectores de 30px",
    que: "el selector de la barra de filtros mide 30px de `md` para arriba (44px táctiles abajo)",
    archivo: "components/ui/select.tsx",
    debe: ["md:h-[30px]"],
  },
  // ── §3 · Ficha de detalle ────────────────────────────────────────────────────
  {
    seccion: "§3",
    cita: "Barra de identidad: monograma de 46px",
    que: "el monograma de la barra de identidad mide 46px",
    archivo: "components/ui/FichaIdentidad.tsx",
    debe: ["size-[46px]"],
  },
  {
    seccion: "§3",
    cita: "grillas etiqueta-valor de filas de 30px con el valor a la derecha en cifras tabulares",
    que: "la grilla etiqueta-valor: filas de 30px y el valor en cifras tabulares",
    archivo: "components/ui/fichaPanel.tsx",
    debe: ["min-h-[30px]", "tabular-nums"],
  },
  // ── §3 · Modal de formulario ─────────────────────────────────────────────────
  {
    seccion: "§3",
    cita: "Vidrio con blur de 28px sobre scrim al 35%, 460–560px, radio de 14px.",
    que: "el modal de formulario: blur de 28px, scrim al 35% y tope de 560px",
    archivo: "components/ui/dialogClases.ts",
    debe: ["backdrop-blur-[28px]", "bg-black/35", "max-w-[560px]"],
  },
  {
    seccion: "§3",
    cita: "Campos en grilla de dos columnas, alto 34px",
    que: "el campo del modal de formulario mide 34px de `md` para arriba",
    archivo: "components/ui/dialogClases.ts",
    debe: ["h-[34px]"],
  },
  {
    seccion: "§3",
    cita: "el activo lleva borde `--primary` con anillo de 3px",
    que: "el campo con foco: borde `--ring` y anillo de 3px, de fábrica en el primitivo",
    archivo: "components/ui/input.tsx",
    debe: ["focus-visible:border-ring", "focus-visible:ring-3"],
  },
  // ── §3 · Vacío y carga ───────────────────────────────────────────────────────
  {
    seccion: "§3",
    cita: "barras con shimmer de 1,2s",
    que: "el esqueleto usa un shimmer de 1,2s, no el `animate-pulse` de 2s",
    archivo: "app/globals.css",
    debe: ["--animate-shimmer: shimmer 1.2s"],
  },
]

/**
 * Lo que §2 y §3 deciden y este barrido NO puede verificar desde el código, con el motivo.
 * Se declara acá y no se omite: una regla que nadie cubre y nadie nombra vuelve a perderse igual
 * que el hover de tarjeta. Que esté en esta lista significa "lo mira una persona", no "no rige".
 */
const NO_VERIFICABLE: Record<string, string> = {
  "§3 · las acciones por fila siempre visibles":
    "Es la AUSENCIA de un patrón (revelar en hover) repartida por 31 pantallas. Un barrido por " +
    "`group-hover:` marcaría también los íconos que sólo cambian de COLOR al apuntar, que es " +
    "justo lo que la regla pide que hagan.",
  "§3 · el chip es el único relleno azul de la pantalla":
    "Verificable sólo comparando pantalla renderizada contra intención: `bg-primary` legítimo hay " +
    "en el botón primario, en la barra de progreso y en la página actual de la paginación.",
  "§2 · el fondo con manchas de color, azul al 9% y verde al 7%":
    "Vive en el CSS de fondo de la app, y lo que lo justifica es el contraste del texto que va " +
    "encima: eso ya lo mide `app/contrasteTokens.test.ts`, que es el test que corresponde.",
  "§6 · el KPI que requiere acción se despega con el fondo, no con un número en color":
    "Ya lo fija `dashboardBloques.test.tsx` sobre el markup real (el wash en el contenedor y no " +
    "en el <p>). Repetirlo acá sería una segunda definición de la misma regla.",
  "§3 · el título del modal explica la consecuencia, y el error dice qué corregir":
    "Es COPY. `app/pantallasPublicas.test.tsx` cubre la parte que se puede: la lista de mensajes " +
    "genéricos prohibidos. Que una frase explique la consecuencia no se decide con una regex.",
  "§3 · el vacío explica con los valores reales de los filtros":
    "Lo cubre `components/ui/textoVacio.test.ts` sobre el helper que arma la frase, que es donde " +
    "la regla vive de verdad; acá sólo se podría verificar que cada pantalla lo llama.",
}

// ── El barrido de reimplementación ────────────────────────────────────────────

const CARPETAS = ["app", "components"]

/** Rutas relativas a `frontend/`, SIEMPRE con `/`: la normalización vive donde nacen los paths. */
function archivosDe(carpeta: string): string[] {
  const salida: string[] = []
  const recorrer = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (e.name === "node_modules" || e.name.startsWith(".")) continue
      const p = join(dir, e.name)
      if (e.isDirectory()) recorrer(p)
      // Los `.test.*` quedan afuera: no pintan pantalla, y este archivo escribe las clases que
      // busca, así que sin esta línea se marcaría a sí mismo.
      else if (!e.name.includes(".test.") && /\.(tsx?|css)$/.test(e.name)) {
        salida.push(p.slice(RAIZ.length + 1).split(sep).join("/"))
      }
    }
  }
  recorrer(join(RAIZ, carpeta))
  return salida
}

/** Reemplaza el CONTENIDO de los comentarios por espacios, conservando los saltos de línea. */
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

const ARCHIVOS = CARPETAS.flatMap(archivosDe)
const codigoDe = (rel: string) => sinComentarios(readFileSync(join(RAIZ, rel), "utf-8"))

/**
 * El único lugar donde el movimiento al apuntar de una TARJETA se escribe a mano.
 * Es la misma forma que `barridoSelect.test.ts`: migrar sin barrido no cierra nada, porque el
 * próximo hover copiado entra en el próximo PR y la divergencia empieza de vuelta desde uno.
 */
const DUENO_DEL_HOVER = "components/ui/card.tsx"

/** Vidrio: §2 lo permite en el sidebar y en los modales, y en ningún otro lado. */
const VIDRIO_PERMITIDO: Record<string, string> = {
  "components/ui/dialog.tsx": "El scrim del diálogo. §2: vidrio en los modales.",
  "components/ui/dialogClases.ts": "El popup del modal de formulario, con su blur de 28px (§3).",
  "components/features/sucesion/PlanDetallePanel.tsx":
    "El scrim del panel lateral de un plan: es un modal con otra forma — hay algo detrás que " +
    "importa y el panel está adelante, que es la condición que §2 pone para el vidrio.",
  "components/layout/AIPanel.tsx":
    "El scrim del panel de IA en mobile, mismo caso que el anterior: sólo aparece cuando el " +
    "panel se abre encima de la pantalla.",
}

describe("Barrido: las decisiones visuales de §2 y §3 están en el código", () => {
  it("cada decisión declarada sigue escrita en el sistema de diseño", () => {
    // Primero la FUENTE. Si §2 se reescribe, este archivo tiene que releerse antes de que su
    // aserción de código siga pasando: una regla que el documento ya no dice no se defiende.
    expect(DECISIONES.length).toBeGreaterThanOrEqual(14)
    const perdidas = DECISIONES.filter((d) => !DOC.includes(d.cita.replace(/\s+/g, " "))).map(
      (d) => `${d.seccion} · ${d.que} → la cita ya no está en el documento: "${d.cita}"`,
    )
    expect(
      perdidas,
      "el documento cambió debajo de este barrido: releé la sección y actualizá la cita, o sacá " +
        "la decisión si dejó de regir",
    ).toEqual([])
  })

  it("cada decisión está construida en su primitivo", () => {
    const faltan: string[] = []
    for (const d of DECISIONES) {
      const codigo = readFileSync(join(RAIZ, d.archivo), "utf-8")
      for (const clase of d.debe) {
        if (!codigo.includes(clase)) {
          faltan.push(
            `${d.archivo} · ${d.seccion} ${d.que} → falta \`${clase}\` (cita: "${d.cita}")`,
          )
        }
      }
    }
    expect(faltan, "el sistema de diseño pide esto y el primitivo no lo tiene").toEqual([])
  })

  it("lo que §2 prohíbe sigue sin estar", () => {
    const rotas: string[] = []
    for (const d of DECISIONES) {
      // Acá los comentarios se enmascaran: `tablePatron.ts` explica en prosa por qué la fila no
      // se eleva, y esa explicación nombra "elevación" y "shadow" varias veces.
      const codigo = sinComentarios(readFileSync(join(RAIZ, d.archivo), "utf-8"))
      for (const clase of d.noDebe ?? []) {
        if (codigo.includes(clase)) {
          rotas.push(`${d.archivo} · ${d.seccion} ${d.que} → tiene \`${clase}\` (cita: "${d.cita}")`)
        }
      }
    }
    expect(rotas, "esto contradice el sistema de diseño").toEqual([])
  })

  it("nadie reimplementa el movimiento de tarjeta fuera de card.tsx", () => {
    // Guarda de mínimo: sin esto, un recorrido roto descubre 0 archivos y el barrido pasa en el
    // vacío — el falso verde que este repo ya pagó con `barridoFront.test.ts` en Windows.
    expect(ARCHIVOS.length).toBeGreaterThanOrEqual(300)

    const infractores = ARCHIVOS.filter((f) => f !== DUENO_DEL_HOVER).filter((f) => {
      const codigo = codigoDe(f)
      // Los dos síntomas de una copia: la elevación al apuntar, o el par "borde iluminado +
      // sombra" que es como se escribía a mano antes de que existiera la variante.
      return (
        /hover:-?translate-y-/.test(codigo) ||
        (/hover:border-primary/.test(codigo) && /hover:shadow/.test(codigo))
      )
    })
    expect(
      infractores,
      "usá `<Card interactive>` de @/components/ui/card: es el único lugar donde vive el " +
        "movimiento al apuntar de §2 (3px, borde iluminado, 160ms). Y si la tarjeta NO es un " +
        "control, no lleva movimiento — una card informativa que se levanta promete un click " +
        "que no existe.",
    ).toEqual([])
  })

  it("el vidrio sigue siendo sólo del sidebar y de los modales", () => {
    const conVidrio = ARCHIVOS.filter((f) => codigoDe(f).includes("backdrop-blur"))
    // Guarda de mínimo: si el escaneo se rompiera, "no hay vidrio de más" pasaría sin abrir nada.
    expect(conVidrio.length).toBeGreaterThanOrEqual(3)
    expect(
      conVidrio.filter((f) => !(f in VIDRIO_PERMITIDO)),
      "§2: el vidrio va SOLO en el sidebar y en los modales. En una tarjeta de grilla no " +
        "comunica nada y cuesta rendimiento (cada superficie desenfocada obliga a recalcular lo " +
        "de atrás). Si este caso es de verdad un modal, declaralo en VIDRIO_PERMITIDO.",
    ).toEqual([])
  })

  it("cada excepción de vidrio declarada sigue teniendo vidrio", () => {
    // La contracara: una excepción muerta es un permiso abierto para un archivo que ya no lo pide.
    for (const [archivo, razon] of Object.entries(VIDRIO_PERMITIDO)) {
      expect(ARCHIVOS, `la excepción apunta a un archivo inexistente: ${archivo}`).toContain(
        archivo,
      )
      expect(
        codigoDe(archivo).includes("backdrop-blur"),
        `${archivo} ya no usa vidrio: sacá su entrada de VIDRIO_PERMITIDO. ${razon}`,
      ).toBe(true)
    }
  })

  it("lo que este barrido no puede ver está declarado con su motivo", () => {
    // No es decorativo: es lo que impide que "no está en el barrido" se lea como "no rige".
    expect(Object.keys(NO_VERIFICABLE).length).toBeGreaterThanOrEqual(5)
    for (const [regla, motivo] of Object.entries(NO_VERIFICABLE)) {
      expect(regla.startsWith("§"), `${regla} tiene que nombrar su sección`).toBe(true)
      expect(motivo.length, `${regla} no explica por qué no se puede verificar`).toBeGreaterThan(40)
    }
  })
})
