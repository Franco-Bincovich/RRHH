/**
 * 🔴 BARRIDO ESTRUCTURAL — nadie pide un CATÁLOGO que su rol no puede leer.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * LO QUE LO MOTIVÓ, MEDIDO
 * ═══════════════════════════════════════════════════════════════════════════════════
 * `mandos_medios` disparaba **un 403 por cada navegación**: el selector de empresa del sidebar
 * —el único componente presente en TODAS las pantallas— pedía `GET /api/empresas`, gateado por
 * `Seccion.EMPRESA + READ`, que ese rol no tiene. Y otros cuatro más chicos: los filtros de
 * /vacaciones y /ausencias —las DOS secciones que ese rol sí ve— llenan sus selects con
 * `GET /api/areas/opciones` y `GET /api/proyectos`, tampoco legibles para él.
 *
 * Ninguno rompía nada visible: los cinco están detrás de un `.catch(() => {})`. Ese es el
 * problema — un 403 tragado por navegación enseña a ignorar los 403 del log justo en el rol donde
 * importan, y deja un select montado con el catálogo vacío (que `limpiarTodoRestituye` documenta
 * como peor que ningún select: el valor sigue vivo y sigue viajando al backend sin chip que lo
 * quite).
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * EL EJE: DÓNDE PUEDE PASAR, NO "TODO EL QUE PIDE UN CATÁLOGO"
 * ═══════════════════════════════════════════════════════════════════════════════════
 * La primera versión de este archivo barría a TODO consumidor de `fetchEmpresas`/`fetchAreas`/
 * `fetchProyectos` y marcaba 18 archivos — casi todos falsos positivos: modales de /inventario,
 * /objetivos, /periodos, /evaluaciones… Esas pantallas sólo las alcanzan `admin_rrhh` y
 * `gerencia_lectura`, que **pueden leer todo**, así que ahí el 403 no existe y exigir el gate
 * sería ruido puro. Un barrido que marca 18 y acierta 5 no lo mira nadie.
 *
 * El desajuste sólo puede ocurrir donde un rol con permisos ANGOSTOS llega a la pantalla, y hoy
 * ese rol es uno solo: `mandos_medios`, con `MANDOS_MEDIOS_SECCIONES = {vacaciones, ausencias}`.
 * O sea que el alcance real son DOS lugares:
 *   · `components/layout/` — se monta en TODAS las pantallas, incluidas las de ese rol. Es donde
 *     vivía el peor caso: un 403 por navegación.
 *   · Las features de las DOS secciones que ese rol sí ve.
 * Fuera de ahí, el AuthGuard ya garantizó un rol que lee todo.
 *
 * 🚩 DISPARADOR PARA ENSANCHAR ESTO: que aparezca un cuarto rol, o que `MANDOS_MEDIOS_SECCIONES`
 * crezca. El alcance se deriva de esa constante y no de una lista escrita a mano justamente para
 * que el día que crezca, las carpetas nuevas entren solas — por eso el test de abajo la LEE.
 *
 * ⚠️ EL BARRIDO NO DECIDE SI EL PERMISO ESTÁ BIEN. La salida fácil sería darle a `mandos_medios`
 * lectura de áreas y proyectos para que las llamadas no fallen: eso es una decisión de PRODUCTO
 * sobre qué ve ese rol, y tomarla de rebote para callar unos 403 la tomaría del peor modo. Lo que
 * se exige acá es que el front no pida lo que ya está decidido que no puede leer.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR? Las guardas de mínimo corren
 * antes de comparar. Verificado por mutación: sacándole el `useCatalogoPermitido` a
 * `EmpresaSelector`, rojea nombrándolo.
 */
import { readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"

import { describe, expect, it } from "vitest"

const RAIZ = join(__dirname, "..", "..")

/** Los catálogos que llenan selects de pantallas ajenas a su propia sección. */
const CATALOGOS = ["fetchEmpresas", "fetchAreas", "fetchProyectos"] as const

/**
 * Archivos que llaman a un catálogo y NO necesitan el gate, con su razón.
 *
 * 🟢 HOY ESTÁ VACÍA, y con el alcance de arriba es difícil que deje de estarlo: todo lo que entra
 * al barrido está, por construcción, en una pantalla que un rol sin el permiso puede abrir. Una
 * entrada acá tiene que explicar por qué ESE caso no da 403 — no alcanza con "no molesta".
 */
const SIN_GATE: Record<string, string> = {}

function archivosDe(dir: string): string[] {
  const out: string[] = []
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) out.push(...archivosDe(p))
    else out.push(p)
  }
  return out
}

/** Comentarios fuera: varios archivos nombran los catálogos EN PROSA para explicar decisiones. */
function sinComentarios(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "")
}

const TODOS = archivosDe(join(RAIZ, "components"))
  .concat(archivosDe(join(RAIZ, "app")))
  .concat(archivosDe(join(RAIZ, "hooks")))
  .filter((f) => /\.tsx?$/.test(f) && !/\.test\./.test(f))

/**
 * Las secciones que un rol de permisos ANGOSTOS alcanza. Se LEE de `services/permisos.ts` y no
 * se escribe acá: el día que `MANDOS_MEDIOS_SECCIONES` crezca, el alcance de este barrido crece
 * solo. Es la misma razón por la que `barridoEmpresaConcreta` lee los routers del backend.
 */
function seccionesDeRolAngosto(): string[] {
  const src = readFileSync(join(RAIZ, "services", "permisos.ts"), "utf8")
  const bloque = src.slice(src.indexOf("MANDOS_MEDIOS_SECCIONES"))
  const cuerpo = bloque.slice(bloque.indexOf("["), bloque.indexOf("]"))
  return [...cuerpo.matchAll(/"([a-z_]+)"/g)].map((m) => m[1])
}

/** Sólo acá puede haber un 403 por catálogo — ver el encabezado. */
function enAlcance(archivo: string): boolean {
  const partes = archivo.split(/[\\/]/)
  if (partes.includes("layout")) return true
  const i = partes.indexOf("features")
  return i >= 0 && seccionesDeRolAngosto().includes(partes[i + 1] ?? "")
}

/** Los que INVOCAN un catálogo (no los que sólo lo importan o lo nombran en prosa). */
const CONSUMIDORES = TODOS.filter((f) => {
  const src = sinComentarios(readFileSync(f, "utf8"))
  return CATALOGOS.some((c) => src.includes(`${c}(`))
}).filter(enAlcance)

describe("el barrido está mirando algo", () => {
  it("descubre consumidores de los catálogos compartidos", () => {
    expect(CONSUMIDORES.length).toBeGreaterThanOrEqual(3)
  })

  it("barre el árbol entero", () => {
    expect(TODOS.length).toBeGreaterThanOrEqual(300)
  })

  it("el alcance sale de MANDOS_MEDIOS_SECCIONES, no de una lista escrita a mano", () => {
    // Si el parseo de `permisos.ts` se rompe, el alcance colapsa a `layout/` y el barrido pasa
    // habiendo mirado un tercio. Falla acá en vez de en silencio.
    expect(seccionesDeRolAngosto()).toEqual(expect.arrayContaining(["vacaciones", "ausencias"]))
  })
})

describe("ningún catálogo se pide sin permiso de lectura", () => {
  it("todo consumidor gatea con useCatalogoPermitido, o está declarado", () => {
    const sinGate = CONSUMIDORES
      .filter((f) => !sinComentarios(readFileSync(f, "utf8")).includes("useCatalogoPermitido"))
      .map((f) => f.split(/[\\/]/).pop() as string)
      .filter((n) => !(n in SIN_GATE))
    expect(sinGate,
      "Estos piden un catálogo sin chequear que el rol pueda leerlo: para `mandos_medios` es un " +
      "403 por carga, tragado por el `.catch`. Usá `useCatalogoPermitido` " +
      "(`hooks/useCatalogoPermitido.ts`) o declaralo en SIN_GATE con su razón.",
    ).toEqual([])
  })

  it("ninguna excepción apunta a un archivo que ya no pide catálogos", () => {
    const nombres = new Set(CONSUMIDORES.map((f) => f.split(/[\\/]/).pop() as string))
    const muertas = Object.keys(SIN_GATE).filter((n) => !nombres.has(n))
    expect(muertas, "Una excepción muerta es ruido que tapa el próximo caso.").toEqual([])
  })

  it("toda excepción tiene razón escrita", () => {
    expect(Object.entries(SIN_GATE).filter(([, v]) => v.trim().length < 30).map(([k]) => k))
      .toEqual([])
  })
})
