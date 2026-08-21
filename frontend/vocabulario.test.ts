import { readdirSync, readFileSync, statSync } from "node:fs"
import { join, resolve, sep } from "node:path"

import { describe, expect, it } from "vitest"

/**
 * 🔴 BARRIDO ESTRUCTURAL — ningún TEXTO VISIBLE dice "Empleado" ni "Recursos Humanos".
 *
 * El sistema de diseño §4 fija el vocabulario: se dice **Colaboradores**, no empleados, y
 * **Capital Humano**, no Recursos Humanos. El renombre va en pantalla, en los encabezados y
 * nombres de archivo de export, y en los mensajes de error visibles. NO va en tablas, columnas,
 * endpoints, el valor `entidad` de la auditoría, ni en identificadores de código.
 *
 * 🔑 CÓMO DISTINGUE TEXTO DE IDENTIFICADOR, que es lo único que hace usable a este barrido.
 * Un barrido que marque `const empleados = ...` o `import { fetchEmpleados }` es un barrido que
 * alguien apaga en dos semanas, y con razón. Por eso NO mira código: mira dos superficies, y
 * solo dos.
 *
 *   1. **Literales de string** (`"..."`, `'...'`, `` `...` ``) que parezcan PROSA — que tengan
 *      un espacio, o sean una palabra sola capitalizada. `"empleado_id"`, `"/api/empleados"`,
 *      `"@/services/empleados"` y `"empleados"` en minúscula (una clave, una sección, un valor
 *      de `entidad`) NO son prosa y no se miran.
 *   2. **Texto JSX** entre `>` y `<`, que por definición es lo que el usuario lee.
 *
 * Y antes de buscar, ENMASCARA lo que adentro de una frase sigue siendo código: las
 * interpolaciones `${...}` (ahí vive `empleado.nombre`, un campo) y las variables de plantilla
 * `{{...}}` (ahí vive `nombre_empleado`, que es el nombre real de una variable de mail definida
 * por la allowlist del backend). Sin ese enmascarado el barrido empujaría a renombrar cosas que
 * romperían el envío de mails.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
 *   · El descubrimiento es por lectura del árbol; ningún archivo está en una lista.
 *   · Guardas de mínimo ANTES de comparar: si el escaneo se rompiera, encontraría 0 literales
 *     y "no hay violaciones" pasaría en el vacío.
 *   · Las excepciones se verifican en las DOS direcciones: que lo declarado exista, y que no
 *     quede ninguna violación sin declarar. Una excepción muerta es rojo, igual que una viva
 *     sin declarar.
 */

const RAIZ = resolve(__dirname, "..")
/**
 * 🔴 `types/` Y `utils/` ENTRARON EL 21/8/2026, Y LA OMISIÓN NO ERA INOCENTE: en `types/auth.ts`
 * vive `ROL_LABEL`, el mapa de etiquetas de rol que /configuracion pinta en pantalla, y decía
 * **"Administrador RRHH"**. Se vio en una captura, no acá. La lección es la de siempre en este
 * repo: un barrido que elige carpetas por dónde uno *supone* que hay texto visible no cubre lo
 * que el código hace de verdad — las etiquetas de una unión de tipos viven con el tipo.
 */
const CARPETAS = [
  "frontend/app", "frontend/components", "frontend/services", "frontend/hooks", "frontend/lib",
  "frontend/types", "frontend/utils",
]

// Las excepciones son (archivo, fragmento, razón). Ninguna es "por ahora": cada una explica por
// qué ESE texto sigue siendo el correcto.
const EXCEPCIONES: ReadonlyArray<{ archivo: string; fragmento: string; razon: string }> = [
  {
    archivo: "frontend/components/features/comunicacion/PlantillaCampos.tsx",
    fragmento: "Hola {{nombre_empleado}}, ...",
    razon:
      "`nombre_empleado` es el nombre REAL de una variable de plantilla de mail, definido por " +
      "la allowlist del backend (services/mailer/_variables). Renombrarlo en el placeholder le " +
      "enseñaría a Capital Humano una variable que no existe y el mail saldría con el literal.",
  },
]

function archivosDe(dir: string): string[] {
  const salida: string[] = []
  const caminar = (d: string) => {
    for (const e of readdirSync(d)) {
      if (e === "node_modules" || e === ".next") continue
      const p = join(d, e)
      if (statSync(p).isDirectory()) caminar(p)
      else if ((p.endsWith(".ts") || p.endsWith(".tsx")) && !p.includes(".test.")) {
        salida.push(p.split(sep).join("/"))
      }
    }
  }
  caminar(dir)
  return salida
}

const ARCHIVOS = CARPETAS.flatMap((c) => archivosDe(join(RAIZ, c)))

/** Reemplaza por espacios lo que dentro de una frase sigue siendo código. */
function enmascarar(s: string): string {
  return s.replace(/\$\{[^}]*\}/g, (m) => " ".repeat(m.length)).replace(/\{\{[^}]*\}\}/g, (m) => " ".repeat(m.length))
}

/** ¿Este literal es prosa que un usuario lee, o un identificador? */
function esProsa(s: string): boolean {
  if (s.includes("/") || s.includes("@") || s.startsWith(".")) return false // rutas e imports
  if (/^[a-z][\w]*$/.test(s)) return false // clave, sección, valor de entidad
  if (/^[\w.]+\(\)?/.test(s) && !s.includes(" ")) return false // referencia a código
  return s.includes(" ") || /^[A-ZÁÉÍÓÚÑ]/.test(s)
}

const PROHIBIDO = /\bEmplead[oa]s?\b|\bRecursos Humanos\b|\bRRHH\b/i
const LITERAL = /"([^"\n]*)"|'([^'\n]*)'|`([^`\n]*)`/g

/**
 * 🔴 EL TEXTO JSX SE BUSCA EN EL ARCHIVO ENTERO, NO LÍNEA POR LÍNEA — arreglado el 21/8/2026.
 *
 * La versión anterior exigía el `>` y el `<` **en la misma línea**, y en este repo el texto de un
 * botón va casi siempre solo en su renglón:
 *
 *     <Button className="min-h-11" onClick={onNuevo}>
 *       <Plus />
 *       Nuevo empleado          ← ni `>` ni `<` en esta línea: el barrido no la veía
 *     </Button>
 *
 * Así pasaron **12 textos visibles** que dicen "empleado", incluido el botón primario de
 * /empleados y "Asignar empleados" en la ficha de un proyecto. El barrido estaba en verde y la
 * pantalla incumplía §4: es el modo de falla que este repo documenta en su regla transversal —un
 * test que no puede fallar— con otra ropa.
 *
 * El tramo abre en `>` **o en `}`** (el texto que sigue a una interpolación: `{n} empleados sin
 * superior`) y cierra en `<` o en `{`.
 */
const JSX_TEXTO = /([>}])([^<>{}"'`]*?)([<{])/g

/**
 * ¿Ese tramo entre `>` y `<` es texto que alguien lee, o código que quedó en el medio?
 * Sin este filtro, `arr.filter((e) => e.empleados < 3)` daría el tramo `" e.empleados "` y el
 * barrido pediría renombrar un CAMPO. Se rechaza lo que tiene forma de código y se conserva la
 * puntuación de prosa —el punto y la coma— que aparece en cualquier frase de una pantalla.
 */
function esTextoJsx(bruto: string, abre: string, cierra: string): boolean {
  const t = bruto.trim()
  if (!t) return false
  if (/[=;`[\]]|=>|&&|\|\||\?\?/.test(t)) return false // operadores
  if (/\w\(/.test(t)) return false // `contar(` — una llamada. El paréntesis de prosa lleva espacio
  if (t.includes(")") && !t.includes("(")) return false // cierra un paréntesis que abrió el código
  if (/\w\.\w/.test(t)) return false // `empleado.nombre`: acceso a propiedad, no una frase
  /*
   * 🔑 UN TRAMO PEGADO A UNA INTERPOLACIÓN ES TEXTO POR CONSTRUCCIÓN, aunque sea UNA sola
   * palabra. Es lo que cazó el encabezado de `SuperioresPendientesPanel`:
   *     {items.length} empleado{items.length !== 1 ? "s" : ""} sin superior asignado
   * El tramo entre las dos llaves es exactamente `empleado`, un token solo, y la regla de abajo
   * —pensada para no marcar identificadores sueltos entre `>` y `<`— lo dejaba pasar.
   */
  const entreLlaves = abre === "}" || cierra === "{"
  if (!entreLlaves && !/\s/.test(t)) return false // un solo token es un identificador, no una frase
  return /[A-Za-zÁÉÍÓÚÑáéíóúñ]/.test(t)
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

interface Hallazgo { archivo: string; linea: number; texto: string }

function violaciones(): Hallazgo[] {
  const out: Hallazgo[] = []
  const anotar = (rel: string, linea: number, s: string) => {
    if (!PROHIBIDO.test(enmascarar(s))) return
    if (EXCEPCIONES.some((e) => rel === e.archivo && s.includes(e.fragmento))) return
    if (out.some((v) => v.archivo === rel && v.linea === linea && v.texto === s)) return
    out.push({ archivo: rel, linea, texto: s })
  }

  for (const p of ARCHIVOS) {
    const rel = p.slice(p.indexOf("frontend/"))
    const crudo = readFileSync(p, "utf-8")

    // Pasada 1 — LITERALES, línea por línea: ahí el número de línea sale gratis.
    const lineas = crudo.split("\n")
    for (let i = 0; i < lineas.length; i++) {
      const cruda = lineas[i]
      const trim = cruda.trim()
      if (trim.startsWith("//") || trim.startsWith("*") || trim.startsWith("/*")) continue
      for (const m of cruda.matchAll(LITERAL)) {
        const s = m[1] ?? m[2] ?? m[3] ?? ""
        if (esProsa(s)) anotar(rel, i + 1, s)
      }
    }

    // Pasada 2 — TEXTO JSX, sobre el archivo ENTERO y con los comentarios enmascarados: el texto
    // de un botón vive en su propio renglón y línea por línea no se ve.
    const codigo = sinComentarios(crudo)
    for (const m of codigo.matchAll(JSX_TEXTO)) {
      const [, abre, texto, cierra] = m
      if (!esTextoJsx(texto, abre, cierra)) continue
      const hasta = (m.index ?? 0) + m[0].indexOf(texto)
      anotar(rel, codigo.slice(0, hasta).split("\n").length, texto.trim())
    }
  }
  return out
}

const VIOLACIONES = violaciones()

describe("guardas del barrido de vocabulario", () => {
  it("se leyó el árbol del front", () => {
    expect(ARCHIVOS.length).toBeGreaterThanOrEqual(300)
  })

  it("el clasificador distingue prosa de identificador", () => {
    // Ancla la heurística con casos literales ANTES de creerle nada a la medición de arriba.
    expect(esProsa("No hay colaboradores activos")).toBe(true)
    expect(esProsa("Colaborador")).toBe(true)
    expect(esProsa("empleado_id")).toBe(false)
    expect(esProsa("empleados")).toBe(false)
    expect(esProsa("/api/empleados")).toBe(false)
    expect(esProsa("@/services/empleados")).toBe(false)
    expect(PROHIBIDO.test(enmascarar("${empleado.nombre} ${empleado.apellido}"))).toBe(false)
    expect(PROHIBIDO.test(enmascarar("Hola {{nombre_empleado}}"))).toBe(false)
    expect(PROHIBIDO.test("No hay empleados activos")).toBe(true)
  })
})

describe("el vocabulario del sistema de diseño §4", () => {
  it("ningún texto visible dice Empleado ni Recursos Humanos", () => {
    expect(
      VIOLACIONES.map((v) => `${v.archivo}:${v.linea}  ${JSON.stringify(v.texto)}`),
      'Se dice "Colaboradores" y "Capital Humano" (sistema de diseño §4). Si alguno de estos ' +
        "textos tiene que quedarse como está, declaralo en EXCEPCIONES CON su razón.",
    ).toEqual([])
  })

  it.each(EXCEPCIONES)("la excepción de $archivo sigue viva", (e) => {
    // Una excepción muerta es ruido que oculta el próximo caso real.
    const src = readFileSync(join(RAIZ, e.archivo), "utf-8")
    expect(src.includes(e.fragmento), `la excepción ya no está en el archivo: ${e.fragmento}`).toBe(true)
    expect(e.razon.length).toBeGreaterThan(40)
  })
})
