import { readdirSync, readFileSync, statSync } from "node:fs"
import { join, resolve, sep } from "node:path"

import { describe, expect, it } from "vitest"

/**
 * 🔴 BARRIDO ESTRUCTURAL DEL FRONT — falla cuando `services/` exporta algo que ninguna
 * pantalla importa.
 *
 * POR QUÉ EXISTE. El backend tiene este barrido desde hace varias sesiones
 * (`backend/tests/test_callers_huerfanos.py`); el front no lo tenía, y el hueco se pagó:
 * `fetchCliente` nació sin un solo caller y sobrevivió cinco sesiones.
 *
 * 🔑 Y LO PEOR NO ES LA FUNCIÓN MUERTA, ES LO QUE TAPA. El barrido de endpoints del backend
 * empareja (path, método) contra los LITERALES de path que aparecen escritos en el front —no
 * contra las funciones que de verdad se llaman—, así que un wrapper muerto le sigue "dando
 * caller" a su endpoint. El GET de cliente por id quedó tapado por `updateCliente` y
 * `deleteCliente`, que escriben el mismo literal con otro método. Este barrido mira el otro
 * eje —quién IMPORTA a quién— y por eso ve lo que aquél no puede.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *   · El descubrimiento es por lectura del árbol: no hay ninguna lista escrita a mano de qué
 *     mirar. Un service nuevo entra solo, y una función nueva sin punta lo pone en rojo.
 *   · Las guardas de mínimo corren ANTES de comparar: si el escaneo se rompe, el barrido
 *     encuentra 0 exports y 0 imports, y "nadie está huérfano" pasaría en el vacío.
 *   · Las excepciones se verifican en las DOS direcciones, igual que en el backend: que lo
 *     huérfano esté declarado, y que lo declarado siga huérfano.
 *
 * 🚩 LOS CUATRO FALSOS POSITIVOS QUE PRODUCÍA, resueltos (sin ellos nacía con ~13 huérfanas
 * falsas, y un barrido que grita se apaga):
 *   1. USO DENTRO DEL PROPIO MÓDULO. `createAusencia` la llama otra función del mismo archivo,
 *      así que no hay ningún `import` que la nombre. Se cuenta como viva.
 *   2. RE-EXPORTS. `services/auth.ts` re-exporta `refreshSession` desde `services/authRefresh`;
 *      quien la importa de `auth` es caller de la de `authRefresh`. Se sigue la cadena.
 *   3. COLISIÓN DE NOMBRES ENTRE MÓDULOS. Hay dos `createAsignacion` (proyectos y
 *      capacitaciones) y `setPresupuesto` es además un setter de `useState` en un componente.
 *      Por eso el emparejamiento es por (MÓDULO, nombre) y nunca por identificador suelto: un
 *      grep del nombre habría dado por vivas a las dos, que es justo el error a evitar.
 *   4. IMPORTS DE TIPO. `import { type X }` y `import type {...}` no son callers de nada.
 *
 * 🚩 LO QUE NO CUBRE: `import * as ns from "@/services/x"` (hoy no existe ninguno; si aparece,
 * sobre-contaría) y los `await import(...)` dinámicos, que hoy solo hay en tests y apuntan a
 * componentes. Los dos sobre-cuentan callers —dan por viva una función muerta—, nunca al
 * revés: este barrido no puede inventar un huérfano.
 */

const RAIZ = resolve(__dirname, "..")
const CARPETAS = ["app", "components", "hooks", "services"]

const RE_EXPORT = /^export\s+(?:async\s+)?(?:function\s+(\w+)|const\s+(\w+)\s*[:=])/gm
const RE_IMPORT = /import\s+(type\s+)?\{([\s\S]*?)\}\s*from\s*["']([^"']+)["']/g
const RE_REEXPORT = /export\s+\{([\s\S]*?)\}\s*from\s*["']([^"']+)["']/g

// ── Excepciones declaradas ────────────────────────────────────────────────────
// Cada una lleva su razón: si alguien agrega una sin justificarla, se ve en el diff.
// 🔴 Ninguna de estas es "está bien así": son features publicadas e inalcanzables desde la UI.
// La lista es el inventario que el front no tenía, no una amnistía.

const PENDIENTE_NO_INTENCIONAL: Record<string, string> = {
  "@/services/costos::setPresupuesto":
    "🔴 PENDIENTE, NO INTENCIONAL. `POST /api/costos/presupuesto` NO tiene otra punta en el " +
    "front: esta función es el único lugar donde se escribe ese path, así que fijar un " +
    "presupuesto es hoy inalcanzable desde la UI. Encaja con lo verificado en producción: " +
    "cero eventos `set_presupuesto` en auditoría. Conectarla es una tanda propia.",

  "@/services/proyectos::createAsignacion":
    "🔴 PENDIENTE, NO INTENCIONAL. La asignación SINGLE a un proyecto. La pantalla usa el " +
    "bulk (`/asignaciones/bulk`) y el alta por área, que son otros paths, así que el endpoint " +
    "single quedó publicado sin puerta. El barrido del backend no lo ve porque " +
    "`fetchAsignaciones` escribe el MISMO literal con GET.",

  "@/services/proyectos::deleteProyecto":
    "🔴 PENDIENTE, NO INTENCIONAL. La pantalla de proyectos no ofrece borrar. Molde para " +
    "conectarlo cuando se decida: el borrado con confirmación de Vacantes.",

  "@/services/assessment::createLink":
    "assessment está apagado por ASSESSMENT_ENABLED y su router ni se monta. El módulo entero " +
    "queda fuera de alcance hasta que se encienda; que no haya alta de link se revisa ahí.",

  "@/services/empresa::fetchEmpresaConfig":
    "🔴 PENDIENTE, NO INTENCIONAL. Devuelve nombre y logo de la PRIMERA empresa, que era la " +
    "forma mono-empresa de resolverlo. Con dos empresas cargadas ya no significa nada estable: " +
    "o se conecta contra la empresa activa del selector, o se borra. No se toca en esta tanda " +
    "porque decidirlo es producto, no limpieza.",

  "@/services/empresaStore::subscribeEmpresaActiva":
    "🔴 PENDIENTE, NO INTENCIONAL. Es la mitad suscriptora del store de empresa activa: nadie " +
    "se suscribe, así que un cambio de empresa no notifica a nadie por esta vía (las " +
    "pantallas releen por otro camino). Borrarla deja el store a medias; conectarla cambia " +
    "cómo se propaga la vista. Las dos son decisión, no limpieza.",
}

// Wrappers `GET /{id}` que nadie usa porque la pantalla ya tiene el objeto del listado.
// Es el MISMO caso que `fetchCliente`, que se borró el 2026-08-10. La diferencia es que
// aquéllos son módulos ajenos a esta tanda: se declaran ahora y se barren cuando se toque
// cada módulo. Están acá para que el próximo que nazca se distinga de éstos.
const WRAPPER_POR_ID_SIN_USO =
  "wrapper GET por id sin caller: la pantalla ya tiene la fila del listado. MISMO caso que " +
  "`fetchCliente` (borrada el 2026-08-10). ⚠️ Mientras exista, TAPA a su endpoint del barrido " +
  "de `test_callers_huerfanos.py`, que cuenta literales de path y no callers. Se borra al " +
  "tocar su módulo."

const SIN_CALLER: Record<string, string> = {
  ...PENDIENTE_NO_INTENCIONAL,
  "@/services/areas::fetchArea": WRAPPER_POR_ID_SIN_USO,
  "@/services/inventario::fetchItem": WRAPPER_POR_ID_SIN_USO,
  "@/services/vacaciones::fetchVacacion": WRAPPER_POR_ID_SIN_USO,
  "@/services/vacaciones::updateVacacion":
    "🔴 PENDIENTE, NO INTENCIONAL. La edición de una solicitud de vacaciones. La pantalla " +
    "aprueba, rechaza y cancela —cada una con su endpoint—, pero no edita. Distinto de los " +
    "wrappers GET de arriba: acá falta una acción, no sobra un atajo.",
}

// ── Guardas de mínimo ─────────────────────────────────────────────────────────
// Criterio: ~25% por debajo del valor real de hoy (263 exports, 438 archivos, 792 imports),
// el mismo que usa el barrido del backend. El margen absorbe la baja normal del repo sin
// absorber una ROTURA del escaneo, que no baja un 25%: colapsa a cero.
const MINIMO_EXPORTS = 200
const MINIMO_ARCHIVOS = 330
const MINIMO_IMPORTS = 600

// ── Escaneo ───────────────────────────────────────────────────────────────────

/**
 * 🔴 LOS PATHS SALEN NORMALIZADOS A "/" Y NO ES COSMÉTICO — es lo único que hace que este
 * barrido vea algo en Windows.
 *
 * `path.join` usa el separador del sistema (`\` en Windows), y abajo hay dos lugares que
 * comparan contra un "/" literal: el filtro `includes("/services/")` y el `split("/")` de
 * `moduloDe`. Sin normalizar, ninguno matchea nunca: `SERVICES` queda vacío, `EXPORTS` también,
 * y el barrido reporta **0 exports** — o sea, "nadie está huérfano" sobre un conjunto vacío.
 *
 * Lo cazaron las guardas de mínimo (`expected 0 to be >= 200`), que es exactamente para lo que
 * están. Pero el síntoma era **por plataforma**: verde en la Mac, tres rojos en la Lenovo, sin
 * que hubiera cambiado una línea del código auditado.
 *
 * Se normaliza acá, en el ÚNICO lugar donde nacen los paths, y no en cada comparación: si se
 * arregla en los dos consumidores, el tercero que se agregue vuelve a nacer con el bug.
 * `readFileSync` acepta "/" en Windows, así que no hay nada más que tocar.
 */
function archivosDe(dir: string): string[] {
  const salida: string[] = []
  const caminar = (d: string) => {
    for (const e of readdirSync(d)) {
      const p = join(d, e)
      if (statSync(p).isDirectory()) caminar(p)
      else if (p.endsWith(".ts") || p.endsWith(".tsx")) salida.push(p.split(sep).join("/"))
    }
  }
  caminar(dir)
  return salida
}

/** Los nombres de un bloque `{ a, b as c, type D }`, sin los de tipo y sin el alias. */
function especificadores(bloque: string): string[] {
  return bloque
    .split(",")
    .map((e) => e.trim())
    .filter((e) => e && !e.startsWith("type "))
    .map((e) => e.split(" as ")[0].trim())
    .filter(Boolean)
}

const esTest = (p: string) => p.includes(".test.")
const moduloDe = (p: string) => `@/services/${p.split("/").pop()!.replace(/\.tsx?$/, "")}`

const ARCHIVOS = CARPETAS.flatMap((c) => archivosDe(join(RAIZ, c)))
const SERVICES = ARCHIVOS.filter((p) => p.includes("/services/") && !esTest(p))

/** (módulo → nombres exportados) y (módulo → nombres que se usan DENTRO de su propio archivo). */
const EXPORTS = new Map<string, Set<string>>()
const USO_PROPIO = new Map<string, Set<string>>()
for (const p of SERVICES) {
  const src = readFileSync(p, "utf-8")
  const mod = moduloDe(p)
  for (const m of src.matchAll(RE_EXPORT)) {
    const nombre = m[1] ?? m[2]
    if (!EXPORTS.has(mod)) EXPORTS.set(mod, new Set())
    EXPORTS.get(mod)!.add(nombre)
    // Falso positivo 1: más de una aparición ⇒ alguien del propio archivo la usa.
    if (src.match(new RegExp(`\\b${nombre}\\b`, "g"))!.length > 1) {
      if (!USO_PROPIO.has(mod)) USO_PROPIO.set(mod, new Set())
      USO_PROPIO.get(mod)!.add(nombre)
    }
  }
}

/** Falso positivo 2: (móduloQueReExporta, nombre) → módulo que de verdad lo define. */
const REEXPORTS = new Map<string, string>()
for (const p of SERVICES) {
  const src = readFileSync(p, "utf-8")
  for (const m of src.matchAll(RE_REEXPORT)) {
    for (const n of especificadores(m[1])) REEXPORTS.set(`${moduloDe(p)}::${n}`, m[2])
  }
}

const IMPORTADO_POR_PROD = new Set<string>()
const IMPORTADO_POR_TEST = new Set<string>()
let totalImports = 0
for (const p of ARCHIVOS) {
  const src = readFileSync(p, "utf-8")
  const propio = moduloDe(p)
  const destino = esTest(p) ? IMPORTADO_POR_TEST : IMPORTADO_POR_PROD
  for (const m of src.matchAll(RE_IMPORT)) {
    if (m[1]) continue // `import type { ... }` — falso positivo 4
    const mod = m[3]
    if (mod === propio) continue
    for (const n of especificadores(m[2])) {
      if (!esTest(p)) totalImports++
      destino.add(`${mod}::${n}`)
      const origen = REEXPORTS.get(`${mod}::${n}`)
      if (origen) destino.add(`${origen}::${n}`)
    }
  }
}

const TODOS = [...EXPORTS.entries()].flatMap(([mod, ns]) =>
  [...ns].map((n) => ({ clave: `${mod}::${n}`, mod, n })),
)
const VIVOS = TODOS.filter(
  (e) => IMPORTADO_POR_PROD.has(e.clave) || USO_PROPIO.get(e.mod)?.has(e.n),
)
const SIN_PROD = TODOS.filter((e) => !VIVOS.includes(e))
const HUERFANOS = SIN_PROD.filter((e) => !IMPORTADO_POR_TEST.has(e.clave)).map((e) => e.clave)
const SOLO_TESTS = SIN_PROD.filter((e) => IMPORTADO_POR_TEST.has(e.clave)).map((e) => e.clave)

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("el barrido está mirando algo", () => {
  it("descubre los exports de services/", () => {
    expect(TODOS.length).toBeGreaterThanOrEqual(MINIMO_EXPORTS)
  })

  it("descubre los archivos del front", () => {
    expect(ARCHIVOS.length).toBeGreaterThanOrEqual(MINIMO_ARCHIVOS)
  })

  it("descubre los imports de producción", () => {
    // Si el árbol no se lee, TODAS las funciones saldrían huérfanas a la vez.
    expect(totalImports).toBeGreaterThanOrEqual(MINIMO_IMPORTS)
  })
})

describe("exports de services/ sin caller", () => {
  it("ninguno huérfano sin declarar", () => {
    // Nadie la importa: ni una pantalla, ni otro service, ni un test.
    expect(HUERFANOS.filter((c) => !(c in SIN_CALLER))).toEqual([])
  })

  it("ninguno solo-de-tests sin declarar", () => {
    // El bucket peligroso: PARECE viva porque la suite la ejercita, y producción no la alcanza.
    expect(SOLO_TESTS.filter((c) => !(c in SIN_CALLER))).toEqual([])
  })

  it("las excepciones siguen sin caller", () => {
    // Dirección inversa: una excepción que ya tiene caller (o que apunta a una función
    // borrada) es ruido que oculta el próximo caso.
    const vigentes = new Set([...HUERFANOS, ...SOLO_TESTS])
    expect(Object.keys(SIN_CALLER).filter((c) => !vigentes.has(c))).toEqual([])
  })

  it("toda excepción tiene razón escrita", () => {
    // Una lista pelada no se puede auditar: en seis meses nadie sabe por qué está cada una.
    expect(Object.entries(SIN_CALLER).filter(([, r]) => r.trim().length < 20).map(([c]) => c))
      .toEqual([])
  })

  it("fetchCliente no volvió", () => {
    // El caso que motivó el barrido. Su endpoint queda publicado por completitud REST y está
    // declarado en backend/tests/test_callers_huerfanos.py; el wrapper no vuelve.
    expect(EXPORTS.get("@/services/clientes")).not.toContain("fetchCliente")
  })
})
