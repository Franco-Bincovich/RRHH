import { readdirSync, readFileSync } from "node:fs"
import { join, resolve, sep } from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { CargaForm } from "@/components/features/horasPublico/CargaForm"
import { IdentificacionForm } from "@/components/features/horasPublico/IdentificacionForm"
import { FORM_HORAS_VACIO, FORM_LICENCIA_VACIO } from "@/components/features/horasPublico/logica"
import { FilaLikert, FilaMultiple } from "@/components/features/evaluacionPublica/Preguntas"
import { PREGUNTAS_COGNITIVAS, PREGUNTAS_SELF, faltanEnPaso } from "@/components/features/evaluacionPublica/_preguntas"
import { LoginForm } from "@/components/features/auth/LoginForm"
import { EsqueletoAuth } from "@/components/features/auth/MarcaAuth"
import { validarLogin } from "@/components/features/auth/_loginForm"
import { CambiarPasswordForm } from "@/components/features/usuarios/CambiarPasswordForm"
import { EMPTY, validarCambio } from "@/components/features/usuarios/_cambiarPassword"
import { AvisoError } from "@/components/ui/AvisoError"
import { PasswordField } from "@/components/features/usuarios/_fields"

/**
 * 🔴 BARRIDO ESTRUCTURAL — LAS CUATRO PANTALLAS FUERA DE `(dashboard)`.
 *
 * POR QUÉ TIENEN SU PROPIO ARCHIVO. `/login`, `/horas`, `/evaluacion/[token]` y
 * `/cambiar-password` son las ÚNICAS que ve alguien de afuera del equipo de Capital Humano: el
 * colaborador que carga sus horas desde el teléfono, la persona que responde una evaluación. Y
 * son las que quedaron afuera de todo: **ninguno de los tres estados compartidos —`EmptyState`,
 * `ErrorState`, `Skeleton`— había cruzado la frontera de `(dashboard)`**, así que cada una
 * resolvía carga, error y vacío a su manera. Lo que este barrido fija es que no vuelvan a
 * separarse.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *   · (a) renderiza las CUATRO páginas de verdad. Sin jsdom los `useEffect` no corren, así que lo
 *     que se ve es el estado inicial — que es justamente el de CARGA. Un `return null` o un
 *     spinner escrito a mano rojea. La parte de ERROR no se puede alcanzar por render (necesita
 *     estado), así que se verifica por FUENTE: que ninguna de estas pantallas vuelva a escribir
 *     su propia caja roja ni su propio spinner.
 *   · (b) compara contra los mensajes REALES, y además rechaza los genéricos por lista: un
 *     "Campo inválido" pasaría cualquier `toBeTruthy` y rojea acá.
 *   · (c) recorre el markup REAL buscando cada `<button>`, `<input>` y `<select>`, y exige que
 *     cada uno declare una altura de 44px. No mira una lista de componentes escrita a mano: un
 *     control nuevo en cualquiera de estos formularios entra solo.
 *   · (d) enmascara los comentarios antes de buscar. Es obligatorio: `logica.ts`, `fechas.ts`,
 *     `SemanaTabla.tsx` y `CamposCarga.tsx` **explican en prosa** por qué NO usan esos patrones,
 *     y un barrido por texto plano los marcaría a los cuatro — con la salida "natural" de borrar
 *     las explicaciones.
 */

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: () => {}, push: () => {} }),
  useParams: () => ({ token: "tok" }),
}))

const RAIZ = resolve(__dirname, "..")

/** Las carpetas que forman las cuatro pantallas públicas, con lo que cada una arrastra. */
const CARPETAS_PUBLICAS = [
  "app/login",
  "app/horas",
  "app/evaluacion",
  "app/cambiar-password",
  "components/features/auth",
  "components/features/horasPublico",
  "components/features/evaluacionPublica",
]
/** Los dos archivos de `usuarios/` que sólo `/cambiar-password` y `/login` usan. */
const SUELTOS = [
  "components/features/usuarios/CambiarPasswordForm.tsx",
  "components/features/usuarios/_cambiarPassword.ts",
  "components/features/usuarios/_fields.tsx",
]

function archivosDe(carpeta: string): string[] {
  const salida: string[] = []
  const recorrer = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (e.name.startsWith(".")) continue
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

const PUBLICOS = [...CARPETAS_PUBLICAS.flatMap(archivosDe), ...SUELTOS]
const codigo = (f: string) => sinComentarios(readFileSync(join(RAIZ, f), "utf-8"))

// ─── (a) carga y error con los componentes compartidos ────────────────────────

describe("(a) las cuatro pantallas usan los estados compartidos", () => {
  it("el barrido encontró los archivos de las cuatro", () => {
    // Guarda de mínimo: si el recorrido se rompiera, las aserciones negativas de abajo pasarían
    // sin haber abierto un solo archivo.
    expect(PUBLICOS.length).toBeGreaterThanOrEqual(18)
    for (const f of SUELTOS) expect(PUBLICOS, `falta ${f}`).toContain(f)
  })

  it("ninguna dibuja su propio spinner a mano", () => {
    // El spinner que había en `/evaluacion`: un `<div>` con borde de 4px girando. El `Loader2`
    // adentro de un botón NO es esto —es el estado del botón, no el de la pantalla— y por eso el
    // patrón buscado incluye el borde.
    const culpables = PUBLICOS.filter((f) => /animate-spin[^"']*border-4|border-4[^"']*animate-spin/.test(codigo(f)))
    expect(culpables, "usá <Skeleton shimmer> con la forma de lo que viene (§3)").toEqual([])
  })

  it("ninguna vuelve a escribir su propia caja roja", () => {
    // Las tres versiones que había: `border-destructive/30`, `/40` y `bg-destructive/10`. Ahora
    // es `AvisoError`, que usa los pares `--danger-*` medidos por `app/contrasteTokens.test.ts`.
    const culpables = PUBLICOS.filter((f) => /(?:border|bg)-destructive\/\d/.test(codigo(f)))
    expect(culpables, "usá <AvisoError> de @/components/ui/AvisoError").toEqual([])
  })

  it("ninguna pinta verdes ni ámbares a mano: para eso están los pares de la paleta", () => {
    // `/horas` tenía `emerald-500/10` y `/evaluacion` `emerald-100 dark:emerald-900/30`: dos
    // verdes distintos en dos pantallas públicas para decir lo mismo, y ninguno medido.
    const culpables = PUBLICOS.filter((f) => /\b(?:bg|text|border)-(?:emerald|amber|green|red|yellow)-\d/.test(codigo(f)))
    expect(culpables, "usá --success-*, --warning-* o --danger-* de app/paleta.css").toEqual([])
  })

  it("las cuatro dibujan un esqueleto compartido mientras cargan, no una pantalla en blanco", async () => {
    // Sin jsdom los `useEffect` no corren: lo que sale de un render es el estado INICIAL, que en
    // las cuatro es el de carga. Es la única forma de alcanzarlo, y alcanza para lo que importa.
    const paginas = await Promise.all([
      import("./login/page"),
      import("./cambiar-password/page"),
      import("./horas/page"),
      import("./evaluacion/[token]/page"),
    ])
    for (const [i, mod] of paginas.entries()) {
      const html = renderToStaticMarkup(<mod.default />)
      expect(html.length, `la página ${i} no renderizó nada`).toBeGreaterThan(80)
      expect(html, `la página ${i} no usa el shimmer del sistema de diseño`)
        .toContain("animate-shimmer")
    }
  })

  it("el esqueleto de acceso tiene la forma de la pantalla que viene", () => {
    const html = renderToStaticMarkup(<EsqueletoAuth />)
    // El cuadrado de la marca, el título, el subtítulo y la tarjeta: cuatro barras, no una.
    expect((html.match(/animate-shimmer/g) ?? []).length).toBeGreaterThanOrEqual(4)
  })
})

// ─── (b) mensajes específicos ─────────────────────────────────────────────────

/** Lo que un mensaje NO puede decir: nombra el problema sin decir la salida. */
const GENERICOS = [/^campo inv/i, /^inv[áa]lido$/i, /^error$/i, /requerido$/i, /^dato inv/i]

describe("(b) un formulario con error dice QUÉ corregir", () => {
  it("el login nombra la acción, no el estado del campo", () => {
    const e = validarLogin({ username: "", password: "" })
    expect(e.username).toBe("Ingresá tu usuario")
    expect(e.password).toBe("Ingresá tu contraseña")
  })

  it("el cambio de contraseña nombra la acción en los tres campos", () => {
    const e = validarCambio({ ...EMPTY, nueva: "corta", confirmar: "otra" })
    expect(e.actual).toBe("Ingresá tu contraseña actual")
    expect(e.nueva).toBe("Mínimo 8 caracteres")
    expect(e.confirmar).toBe("Repetí la nueva contraseña: no coinciden")
  })

  it("🔴 una contraseña corta no se compara con la actual: el orden de los if importa", () => {
    // Si el orden se invirtiera, alguien que tipea tres letras iguales a su contraseña actual
    // recibiría "elegí una distinta" y saldría a buscar el problema equivocado.
    const e = validarCambio({ actual: "abc", nueva: "abc", confirmar: "abc" })
    expect(e.nueva).toBe("Mínimo 8 caracteres")
  })

  it("una contraseña larga e igual a la actual sí dice que elija otra", () => {
    const larga = "unacontraseñalarga"
    expect(validarCambio({ actual: larga, nueva: larga, confirmar: larga }).nueva)
      .toBe("Elegí una distinta de la actual")
  })

  it("ningún mensaje de los cuatro formularios es genérico", () => {
    const mensajes = [
      ...Object.values(validarLogin({ username: "", password: "" })),
      ...Object.values(validarCambio({ ...EMPTY, nueva: "x", confirmar: "y" })),
    ]
    expect(mensajes.length).toBeGreaterThanOrEqual(5)
    for (const m of mensajes) {
      for (const g of GENERICOS) {
        expect(g.test(m ?? ""), `"${m}" no dice qué corregir`).toBe(false)
      }
    }
  })

  it("el mensaje por campo llega al markup y se anuncia", () => {
    const html = renderToStaticMarkup(
      <PasswordField id="nueva" label="Nueva" value="" onChange={() => {}} error="Mínimo 8 caracteres" />,
    )
    expect(html).toContain("Mínimo 8 caracteres")
    expect(html).toContain('role="alert"')
    expect(html).toContain('aria-invalid="true"')
    expect(html).toContain('aria-describedby="nueva-error"')
  })

  it("el aviso del servidor no reemplaza el formulario: convive con él", () => {
    const html = renderToStaticMarkup(<AvisoError>Usuario o contraseña incorrectos</AvisoError>)
    expect(html).toContain("Usuario o contraseña incorrectos")
    expect(html).toContain('role="alert"')
    expect(html).toContain("bg-danger-wash")
  })

  it("🔴 /horas y /evaluacion NO tienen mensajes por campo en su primer paso, y por eso no llevan banner", () => {
    // Documentado, no inventado: el DNI se rechaza con RECHAZO ÚNICO del backend (un solo mensaje
    // para cinco motivos distintos), así que no hay nada por campo que decir. Y la evaluación no
    // tiene campos que puedan estar MAL: sólo sin contestar. Un `FormErrores` en cualquiera de
    // los dos diría "Revisá 0 campos".
    expect(codigo("components/features/horasPublico/IdentificacionForm.tsx")).not.toContain("FormErrores")
    expect(codigo("components/features/evaluacionPublica/PreguntasDelPaso.tsx")).not.toContain("FormErrores")
    // Lo que sí tiene la evaluación es la cuenta de lo que falta, que es un dato, no un juicio.
    expect(faltanEnPaso(PREGUNTAS_SELF.map((q) => q.id), {})).toBe(5)
    expect(faltanEnPaso(PREGUNTAS_SELF.map((q) => q.id), { 1: 3, 2: 4, 3: 5, 4: 1, 5: 2 })).toBe(0)
  })
})

// ─── (c) touch targets ────────────────────────────────────────────────────────

/**
 * Las formas de declarar 44px que el repo usa: `h-11`/`min-h-11` (2.75rem) y la variante
 * arbitraria `min-h-[2.75rem]`, más `w-11`/`size-11` para los botones que sólo tienen ícono.
 *
 * ⚠️ LA VARIANTE ENTRE CORCHETES NO PUEDE LLEVAR `\b` AL FINAL, y esto rojeó de verdad al escribir
 * el test: `]` es un carácter no-palabra y el separador de clases es un espacio —también
 * no-palabra—, así que ahí NO hay borde de palabra y `min-h-[2.75rem] w-full` no matcheaba. El
 * falso positivo se leía como un botón sin altura que sí la tenía.
 */
const ALTO_44 = /\b(?:min-)?h-11\b|(?:min-)?h-\[2\.75rem\]|\bw-11\b|\bsize-11\b/

/** Cada tag de control del markup, con su `class`. */
function controles(html: string): { tag: string; clases: string }[] {
  const salida: { tag: string; clases: string }[] = []
  for (const m of html.matchAll(/<(button|input|select)\b([^>]*)>/g)) {
    salida.push({ tag: m[1], clases: /class="([^"]*)"/.exec(m[2])?.[1] ?? "" })
  }
  return salida
}

describe("(c) todo control de las pantallas públicas mide 44px en un teléfono", () => {
  const markups: [string, string][] = [
    ["LoginForm", renderToStaticMarkup(<LoginForm />)],
    ["CambiarPasswordForm", renderToStaticMarkup(<CambiarPasswordForm forced={false} />)],
    ["IdentificacionForm", renderToStaticMarkup(
      <IdentificacionForm dni="123" onDni={() => {}} enviando={false} onSubmit={() => {}} />,
    )],
    ["CargaForm/horas", renderToStaticMarkup(
      <CargaForm modo="horas" onModo={() => {}} horas={FORM_HORAS_VACIO} onHoras={() => {}}
                 licencia={FORM_LICENCIA_VACIO} onLicencia={() => {}}
                 clientes={[{ id: "c1", nombre: "Acme" }]} errores={{}} enviando={false}
                 hoy={new Date(2026, 7, 20)} />,
    )],
    ["CargaForm/licencia", renderToStaticMarkup(
      <CargaForm modo="licencia" onModo={() => {}} horas={FORM_HORAS_VACIO} onHoras={() => {}}
                 licencia={FORM_LICENCIA_VACIO} onLicencia={() => {}} clientes={[]} errores={{}}
                 enviando={false} hoy={new Date(2026, 7, 20)} />,
    )],
    ["FilaLikert", renderToStaticMarkup(
      <FilaLikert pregunta={PREGUNTAS_SELF[0]} elegido={undefined} onElegir={() => {}} />,
    )],
    ["FilaMultiple", renderToStaticMarkup(
      <FilaMultiple pregunta={PREGUNTAS_COGNITIVAS[0]} elegido={undefined} onElegir={() => {}} />,
    )],
  ]

  it("el barrido encontró controles que mirar", () => {
    const total = markups.reduce((n, [, html]) => n + controles(html).length, 0)
    // Guarda de mínimo: si el regex de tags se rompiera, "todos miden 44px" pasaría en el vacío.
    expect(total).toBeGreaterThanOrEqual(30)
  })

  it.each(markups)("%s: ningún botón, input ni select por debajo de 44px", (_nombre, html) => {
    const chicos = controles(html)
      .filter((c) => !ALTO_44.test(c.clases))
      .map((c) => `<${c.tag} class="${c.clases.slice(0, 90)}">`)
    expect(
      chicos,
      "Los primitivos `Input` y `Select` ya miden 44px hasta `md`. Un control con altura propia " +
        "tiene que declararla: `min-h-11` en un botón, `w-11`/`size-11` en uno que sólo tiene ícono.",
    ).toEqual([])
  })

  it("🔴 el `<textarea>` queda fuera, y con razón", () => {
    // Su alto sale de `rows`, no de una clase: los dos de `/horas` usan `rows={2}`, que con el
    // padding del primitivo pasa los 60px. Exigirle una clase de altura sería pedirle que
    // contradiga su propio mecanismo.
    const html = markups.find(([n]) => n === "CargaForm/horas")![1]
    expect(html).toContain("<textarea")
    expect(html).toContain('rows="2"')
  })

  it("los primitivos que estos formularios usan traen los 44px de fábrica", () => {
    // Es donde vive la regla: si alguien se los saca, se rompen las nueve pantallas de una y no
    // hay que acordarse de revisar cada formulario.
    expect(codigo("components/ui/input.tsx"), "el Input perdió el touch target").toContain("h-11 md:h-8")
    expect(codigo("components/ui/select.tsx"), "el Select perdió el touch target").toContain("h-11")
  })
})

// ─── (d) el bug de huso ───────────────────────────────────────────────────────

describe("(d) ninguna pantalla pública formatea fechas con el patrón que corre el día", () => {
  it("nadie usa `new Date(...).toLocaleDateString`", () => {
    // El patrón parsea a medianoche UTC: en Argentina (UTC-3) muestra el día ANTERIOR.
    const culpables = PUBLICOS.filter((f) => /new Date\([^)]*\)\s*\.\s*toLocaleDateString/.test(codigo(f)))
    expect(culpables, "usá `formatFecha` de components/features/shared/fechas.ts").toEqual([])
  })

  it("nadie usa `toISOString().slice(0, 10)`", () => {
    // El patrón inverso: devuelve MAÑANA a partir de las 21:00 hora local. Era el bug de
    // `ventanaFechas`, que ofrecía un día futuro en el calendario de carga de horas.
    const culpables = PUBLICOS.filter((f) => /toISOString\(\)\s*\.\s*slice\(/.test(codigo(f)))
    expect(culpables, "usá `isoLocal` de components/features/shared/fechas.ts").toEqual([])
  })

  it("la prosa NO cuenta: cuatro archivos nombran los dos patrones para explicar por qué no los usan", () => {
    // Sin el enmascarado, estos cuatro serían "culpables" y el arreglo obvio sería borrarles la
    // explicación — que es justo la documentación que hace correcto el código.
    const CON_PROSA = [
      "components/features/horasPublico/logica.ts",
      "components/features/horasPublico/SemanaTabla.tsx",
      "components/features/horasPublico/CamposCarga.tsx",
    ]
    for (const f of CON_PROSA) {
      expect(PUBLICOS, `${f} se movió: actualizá esta lista`).toContain(f)
      const crudo = readFileSync(join(RAIZ, f), "utf-8")
      expect(/toISOString|toLocaleDateString|zona horaria|UTC/.test(crudo), `${f} ya no lo explica`).toBe(true)
      expect(/toISOString\(\)\s*\.\s*slice\(/.test(codigo(f)), `${f} lo usa de verdad`).toBe(false)
    }
  })
})
