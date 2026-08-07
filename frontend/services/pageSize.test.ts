import { existsSync, readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

import { describe, expect, it } from "vitest"

import { MAX_PAGE_SIZE } from "@/services/api"

/**
 * 🔴 BARRIDO ESTRUCTURAL — ningún pedido al listado de empleados puede pasarse de `MAX_PAGE_SIZE`.
 *
 * POR QUÉ EXISTE. Pedir `page_size=200` contra `Query(20, ge=1, le=100)` no devuelve menos filas:
 * devuelve **422**, y el `.catch` de cada hook lo convertía en una lista vacía. Dos modales
 * —envío de plantillas y asignar empleados a un proyecto— mostraron "no hay datos" con 31
 * empleados activos en la base, y la suite entera pasaba en verde.
 *
 * Y pasaba en verde por una razón que este archivo corrige: el único test que tocaba el tema
 * (`empleados.test.ts`) mockea `apiFetch` completo, así que **el fake no puede modelar la
 * validación del backend**. Ese test llamaba con `pageSize: 200` y pasaba. Verificar esto pedía
 * salir del fake y mirar el CÓDIGO REAL de los call sites, que es lo que hace este barrido.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. NO HAY LISTA ESCRITA A MANO de qué mirar: los call sites se descubren leyendo el árbol de
 *    archivos. Un modal nuevo que pida 500 entra solo al barrido y rojea sin tocar este archivo.
 *    Ese es todo el punto — un barrido con lista se olvida del próximo caso.
 * 2. El tope se compara contra `MAX_PAGE_SIZE` IMPORTADO de `services/api`, no contra un `100`
 *    escrito acá. Con un literal, cambiar el `le` del router y el const del front dejaría este
 *    test afirmando un número que ya no rige.
 * 3. GUARDAS DE MÍNIMO antes de comparar (`TestElBarridoEstaMirandoAlgo`): si el descubrimiento
 *    se rompe —cambia el cwd, se renombra `fetchEmpleados`, se excluye mal un directorio— el
 *    barrido devolvería CERO call sites y todos los `every()` de abajo pasarían en el vacío.
 *    Esa es la falla que este bloque muerde, y sin él el archivo entero es decorativo.
 * 4. Un call site que el barrido NO PUEDE RESOLVER hace fallar el test, en vez de saltearse.
 *    Un `pageSize: loQueSea` silenciosamente ignorado sería exactamente el agujero por el que
 *    volvería a entrar el bug.
 *
 * 🚩 LO QUE NO CUBRE, dicho explícito: el valor lo resuelve por lectura de texto, no ejecutando
 * el código. Un `pageSize` que salga de una variable calculada en runtime no se puede resolver
 * acá — y por eso el punto 4 lo hace fallar en lugar de darlo por bueno.
 */

// Desde la URL del módulo y no desde `process.cwd()`: el cwd depende de dónde se invocó a
// vitest, la URL no. Mismo criterio que `loadingSeApaga.test.ts`.
const RAIZ = fileURLToPath(new URL("../", import.meta.url))
const CARPETAS = ["app", "components", "hooks", "services"]

function fuentes(dir: string, out: string[] = []): string[] {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const ruta = join(dir, e.name)
    if (e.isDirectory()) {
      if (e.name !== "node_modules") fuentes(ruta, out)
      // Los .test.* quedan afuera: ejercitan valores a propósito y no llegan al backend real.
    } else if (/\.tsx?$/.test(e.name) && !/\.test\.tsx?$/.test(e.name)) out.push(ruta)
  }
  return out
}

/**
 * El código sin comentarios, conservando los strings.
 *
 * 🔴 HIZO FALTA DE ENTRADA: la primera versión de este barrido se marcó a SÍ MISMA en rojo, por
 * los docstrings que explican el bug y escriben `page_size=200` en prosa. Un barrido que lee
 * comentarios reporta lo que la doc CUENTA, no lo que el código HACE.
 *
 * ⚠️ Límite conocido: un regex literal con `//` adentro (`/https?:\/\//`) se lee como comentario
 * y se come el resto de esa línea. Sub-cuenta, nunca inventa — y las guardas de mínimo muerden
 * si eso llegara a pasar a escala.
 */
function sinComentarios(src: string): string {
  let out = ""
  let i = 0
  while (i < src.length) {
    const c = src[i]
    if (c === "/" && src[i + 1] === "/") {
      while (i < src.length && src[i] !== "\n") i++
    } else if (c === "/" && src[i + 1] === "*") {
      i += 2
      while (i < src.length && !(src[i] === "*" && src[i + 1] === "/")) i++
      i += 2
    } else if (c === '"' || c === "'" || c === "`") {
      out += c
      i++
      while (i < src.length && src[i] !== c) {
        if (src[i] === "\\") { out += src[i]; i++ }
        out += src[i]
        i++
      }
      out += src[i] ?? ""
      i++
    } else {
      out += c
      i++
    }
  }
  return out
}

/** El texto de los argumentos de la llamada que abre en `desde` (index del paréntesis). */
function argumentos(src: string, desde: number): string {
  let profundidad = 0
  for (let i = desde; i < src.length; i++) {
    if (src[i] === "(" || src[i] === "{") profundidad++
    else if (src[i] === ")" || src[i] === "}") {
      profundidad--
      if (profundidad === 0) return src.slice(desde + 1, i)
    }
  }
  return ""
}

interface Llamada {
  archivo: string
  /** Lo que estaba escrito: un número, `MAX_PAGE_SIZE`, o el nombre de un const del módulo. */
  expr: string
  /** El número al que resuelve, o null si el barrido no pudo. */
  valor: number | null
}

/** Resuelve `MAX_PAGE_SIZE`, un literal numérico, o un `const X = <número>` del mismo archivo. */
function resolver(expr: string, src: string): number | null {
  if (/^\d+$/.test(expr)) return Number(expr)
  if (expr === "MAX_PAGE_SIZE") return MAX_PAGE_SIZE
  const m = new RegExp(`const\\s+${expr}\\s*(?::\\s*number\\s*)?=\\s*(\\d+)`).exec(src)
  return m ? Number(m[1]) : null
}

function llamadas(): Llamada[] {
  const out: Llamada[] = []
  const archivos = CARPETAS.flatMap((c) => fuentes(join(RAIZ, c)))
  for (const archivo of archivos) {
    const src = sinComentarios(readFileSync(archivo, "utf8"))
    const rel = archivo.slice(RAIZ.length).replace(/\\/g, "/")

    // (a) fetchEmpleados({ ..., pageSize: X, ... }) — el listado paginado de empleados.
    //     🔴 `cargarEmpleados` VA EN LA MISMA LISTA: es el loader compartido que envuelve a
    //     `fetchEmpleados`, y los dos call sites que tenían el bug pasan por él. Cubrir solo
    //     `fetchEmpleados` dejaba justo esos dos afuera del barrido — el punto ciego se abrió al
    //     extraer el loader, y el barrido siguió pasando porque el resto alcanzaba el mínimo.
    for (const m of src.matchAll(/\b(?:fetchEmpleados|cargarEmpleados)\s*\(/g)) {
      const inicio = m.index! + m[0].length - 1
      // La DECLARACIÓN no es un call site: sus "argumentos" son la firma, y ahí `pageSize:
      // number` haría que el barrido lea el TIPO como si fuera el valor pedido.
      if (/\bfunction\s+$/.test(src.slice(Math.max(0, m.index! - 20), m.index!))) continue
      const args = argumentos(src, inicio)
      const p = /pageSize\s*:\s*([A-Za-z_$][\w$]*|\d+)/.exec(args)
      if (p) out.push({ archivo: rel, expr: p[1], valor: resolver(p[1], src) })
    }

    // (b) `page_size=<n>` escrito a mano en un query string (services/usuarios.ts arma así los
    //     dos selectores de empleados). Va al MISMO endpoint y tiene el MISMO tope.
    for (const m of src.matchAll(/page_size=(\d+)/g)) {
      out.push({ archivo: rel, expr: m[0], valor: Number(m[1]) })
    }
  }
  return out
}

const LLAMADAS = llamadas()

// Hoy son 12: 8 `fetchEmpleados` directos + 2 vía `cargarEmpleados` + 2 query strings a mano.
// El mínimo va con margen para absorber que se borre un modal, no para absorber que el
// descubrimiento se rompa: eso no baja un 25%, colapsa.
const MINIMO_LLAMADAS = 9

describe("el barrido está mirando algo", () => {
  it("🔴 la raíz apunta al front (si no, no lee ningún archivo y todo pasa en el vacío)", () => {
    expect(existsSync(join(RAIZ, "services", "empleados.ts"))).toBe(true)
    for (const c of CARPETAS) expect(existsSync(join(RAIZ, c)), `falta ${c}/`).toBe(true)
  })

  it("🔴 encuentra los call sites reales", () => {
    expect(LLAMADAS.length, `Solo se encontraron ${LLAMADAS.length} pedidos de página. No es que ` +
      "se borraron pantallas: es que el descubrimiento se rompió.").toBeGreaterThanOrEqual(MINIMO_LLAMADAS)
  })

  /**
   * 🔴 UNA LISTA ESCRITA A MANO, Y ESTÁ BIEN QUE LO SEA. No dice QUÉ hay que revisar —eso lo
   * descubre el barrido— sino que el descubrimiento LLEGA a los dos casos conocidos. Hizo falta:
   * al extraer la carga a `cargarEmpleados`, estos dos archivos dejaron de llamar a
   * `fetchEmpleados` y se cayeron del barrido en silencio, que siguió en verde porque los otros
   * ocho alcanzaban el mínimo. Un barrido que pierde justo el caso que lo motivó es peor que no
   * tenerlo, porque además tranquiliza.
   */
  it("🔴 cubre los dos archivos donde vivía el bug", () => {
    for (const a of [
      "components/features/comunicacion/useDestinatarios.ts",
      "components/features/proyectos/useCandidatosProyecto.ts",
    ]) {
      expect(LLAMADAS.some((l) => l.archivo === a), `${a} quedó FUERA del barrido`).toBe(true)
    }
  })

  it("y encuentra los dos SHAPES, no solo uno", () => {
    // Si el regex de (b) dejara de matchear, (a) solo seguiría dando verde y la mitad del
    // barrido estaría apagada sin que nada avise.
    expect(LLAMADAS.some((l) => l.expr.startsWith("page_size="))).toBe(true)
    expect(LLAMADAS.some((l) => !l.expr.startsWith("page_size="))).toBe(true)
  })
})

describe("ningún call site se pasa del tope del backend", () => {
  it("🔴 todos piden <= MAX_PAGE_SIZE", () => {
    const pasados = LLAMADAS.filter((l) => l.valor !== null && l.valor > MAX_PAGE_SIZE)
    expect(pasados, `Estos piden más de ${MAX_PAGE_SIZE} y el backend los rechaza con 422 — la ` +
      "pantalla se queda SIN datos, no con menos: " + JSON.stringify(pasados)).toEqual([])
  })

  it("🔴 y todos se pudieron resolver: un valor opaco es un agujero, no un caso a saltear", () => {
    const opacos = LLAMADAS.filter((l) => l.valor === null)
    expect(opacos, "El barrido no pudo determinar qué page_size piden: " + JSON.stringify(opacos) +
      ". Escribilo como número, como `MAX_PAGE_SIZE`, o como un `const X = <número>` del módulo.")
      .toEqual([])
  })

  it("el tope del front es el mismo que el `le=100` de los routers", () => {
    // Espejo manual del backend: los seis routers paginados declaran `Query(20, ge=1, le=100)`.
    // Si alguien sube el const sin tocar los routers, esto lo frena.
    expect(MAX_PAGE_SIZE).toBe(100)
  })
})

describe("el barrido detecta de verdad un valor prohibido", () => {
  /**
   * Sin esto, "todos piden <= 100" podría estar pasando porque el parser no encuentra NADA.
   * Se le da al resolver el mismo texto que tendría un call site roto y se verifica que lo lea.
   */
  it("🔴 un pageSize de 200 escrito en el código se resuelve a 200 y supera el tope", () => {
    const src = "fetchEmpleados({ page: 1, pageSize: 200, estado: 'activo' })"
    const args = argumentos(src, src.indexOf("("))
    const p = /pageSize\s*:\s*([A-Za-z_$][\w$]*|\d+)/.exec(args)

    expect(p).not.toBeNull()
    expect(resolver(p![1], src)).toBe(200)
    expect(resolver(p![1], src)!).toBeGreaterThan(MAX_PAGE_SIZE)
  })

  it("y un const del módulo también se resuelve (es la forma que usa /empleados)", () => {
    const src = "const PAGE_SIZE = 20\nfetchEmpleados({ page, pageSize: PAGE_SIZE })"
    expect(resolver("PAGE_SIZE", src)).toBe(20)
  })

  it("un identificador que no se puede resolver da null (y arriba eso hace fallar)", () => {
    expect(resolver("loQueSea", "const otraCosa = 5")).toBeNull()
  })
})
