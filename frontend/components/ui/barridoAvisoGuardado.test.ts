/**
 * 🔴 BARRIDO ESTRUCTURAL — todo modal de formulario CONFIRMA cuando el guardado sale bien.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * LO QUE LO MOTIVÓ, MEDIDO
 * ═══════════════════════════════════════════════════════════════════════════════════
 * De los **30 modales de formulario del producto, 29 tenían CERO `toast.success`** (25/8/2026).
 * El único era `CesionModal`. Los ERRORES sí se mostraban y `sonner` ya estaba montado: no
 * faltaba infraestructura, faltaba la mitad buena del par. El circuito era siempre "el modal se
 * cierra, la fila aparece", que alcanza cuando la fila entra en pantalla y no alcanza cuando el
 * listado está paginado, filtrado o en otra pestaña.
 *
 * Arreglar los 29 a mano no cierra nada: el modal número 31 nace mudo. Por eso el barrido.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * EL EJE: "MODAL DE FORMULARIO", NO "COMPONENTE QUE LLAMA A UN SERVICE"
 * ═══════════════════════════════════════════════════════════════════════════════════
 * Se busca el archivo que renderiza un `<DialogContent patron="formulario">` o que se llama
 * `*Modal.tsx` y tiene un submit. Preguntar por "quién llama a un `create*`" obligaría a declarar
 * una excepción por cada hook de carga y cada acción de fila, para siempre — el mismo error de
 * eje que `barridoConfirmacion` evitó eligiendo el verbo HTTP.
 *
 * 🔑 LA UNIDAD ES EL MODAL **MÁS LO QUE IMPORTA, UN SALTO HACIA ABAJO** — el porqué de esa
 * dirección, y de por qué la otra daba falsos verdes, está en `avisa()`.
 *
 * ⚠️ Enmascara comentarios antes de buscar: varios archivos explican EN PROSA por qué NO avisan.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR? Las guardas de mínimo corren
 * antes: si el descubrimiento se rompe, el conjunto colapsa a cero y falla acá. Verificado por
 * mutación: sacándole el aviso a `AreaModal` y a `EventoModal`, rojea nombrando a cada uno. 🔴 La
 * PRIMERA versión de este archivo NO rojeaba con esa mutación —ver la nota de `avisa()`—, así que
 * la calibración del grafo no es un detalle: era la diferencia entre un barrido y un adorno.
 */
import { readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"

import { describe, expect, it } from "vitest"

const RAIZ = join(__dirname, "..", "..")

/**
 * Modales que NO avisan, con su razón. Las cuatro clases están explicadas en el encabezado de
 * `components/features/shared/avisoGuardado.ts`; acá va la lista y el porqué en una línea.
 */
const SIN_AVISO: Record<string, string> = {
  "ImportarFormacionModal.tsx":
    "Termina en un panel de resultado que dice cuántas filas entraron, cuántas se actualizaron y " +
    "cuáles fallaron. Un toast encima sería una confirmación más pobre que la que ya está.",
  "ImportarObjetivosModal.tsx": "Mismo caso que el import de formación: panel de resultado propio.",
  "ImportarNominaModal.tsx": "Mismo caso: `NominaResultView` muestra los tres grupos.",
  "ImportarNominaCSVModal.tsx": "Mismo caso: preview + confirmación con resultado en pantalla.",
  "CrearUsuarioModal.tsx":
    "Su confirmación es `PasswordRevealModal`: la contraseña temporal se muestra UNA sola vez y " +
    "hay que copiarla. Un toast compitiendo por la atención ahí es un riesgo, no una ayuda.",
  "AsignarEmpleadosModal.tsx":
    "Alta en LOTE: `asignarAcciones.ts` ya avisa con la clasificación en tres grupos " +
    "(asignados / ya asignados / errores), que dice más de lo que este helper puede decir.",
  "EditarNominaModal.tsx":
    "No guarda: es presentacional. El submit y su aviso viven en `NominaSection`, su importador.",
  "CampanaModal.tsx":
    "Assessment está apagado (`ASSESSMENT_ENABLED`) y su router ni se monta. Entra al barrido el " +
    "día que se encienda.",
  "NuevoPlanModal.tsx":
    "Sucesión está apagada por dos flags del front y la pantalla redirige antes de montarse.",
  // Modales que no son formularios de guardado: sólo muestran o eligen.
  "AuditDetailModal.tsx": "Sólo muestra el detalle de un evento. No escribe nada.",
  "HistorialModal.tsx": "Sólo muestra el historial de asignaciones de un ítem.",
  "DetalleEmpleadoModal.tsx": "Sólo muestra el detalle de horas de un empleado.",
  "PasswordRevealModal.tsx": "Muestra la contraseña temporal. Es la confirmación, no la acción.",
  "EnviarPlantillaModal.tsx":
    "El envío tiene resultado propio (`EnvioResultado`): enviados, omitidos y fallidos, que es " +
    "justo lo que un toast no puede decir.",
  "AnalisisAreaModal.tsx": "Sucesión, apagada. Y sólo muestra un análisis.",
  "FichaEvaluadoModal.tsx":
    "Sólo MUESTRA la ficha de resultados de un evaluado (competencias, brecha de autopercepción). " +
    "El módulo de evaluaciones no evalúa: importa resultados calculados afuera.",
}

function archivosDe(dir: string): string[] {
  const out: string[] = []
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) out.push(...archivosDe(p))
    else out.push(p)
  }
  return out
}

/** Comentarios fuera: varios archivos explican en prosa por qué no avisan. */
function sinComentarios(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "")
}

const TODOS = archivosDe(join(RAIZ, "components")).concat(archivosDe(join(RAIZ, "app")))
  .filter((f) => /\.tsx?$/.test(f) && !/\.test\./.test(f))

const MODALES = TODOS.filter((f) => f.endsWith("Modal.tsx"))

/**
 * ¿El modal, o algo que IMPORTA a un salto, avisa con el helper compartido?
 *
 * 🔴 DOS CALIBRACIONES, LAS DOS MEDIDAS POR MUTACIÓN, Y LAS DOS IMPORTAN.
 *
 * **(a) El salto va sólo HACIA ABAJO** (lo que el modal importa), no hacia arriba. Abajo hace
 * falta: varios modales delegan el submit a un hook y el aviso vive ahí (`useEmpleadoForm`,
 * `useAusenciaForm`). Arriba se probó y daba FALSOS VERDES: sacándole el aviso a `EventoModal`,
 * el barrido seguía en verde porque `app/(dashboard)/eventos/page.tsx` —que lo importa— tiene un
 * `toast.success` **del borrado**. O sea: la confirmación de OTRA acción tapando la que falta. Es
 * el mismo falso verde que `barridoConfirmacion` midió y evitó con la misma decisión. El único
 * modal que de verdad necesitaba el salto hacia arriba (`EditarNominaModal`, presentacional) se
 * declara en `SIN_AVISO` con su razón, que es más honesto que ensanchar el grafo para todos.
 *
 * **(b) La señal es el HELPER, no `toast.success` a secas.** Aceptar cualquier toast volvía a
 * abrir (a): alcanzaba con que el archivo avisara cualquier otra cosa. Y además es lo que
 * mantiene el vocabulario en un solo lugar, que es la razón por la que el helper existe.
 */
function avisa(modal: string): boolean {
  const propio = sinComentarios(readFileSync(modal, "utf8"))
  const importados = TODOS.filter((f) => {
    const base = f.split(/[\\/]/).pop()!.replace(/\.tsx?$/, "")
    return f !== modal && new RegExp(`from "[^"]*/${base}"`).test(propio)
  })
  return [modal, ...importados].some((f) => {
    const src = sinComentarios(readFileSync(f, "utf8"))
    return src.includes("avisarGuardado") || src.includes("avisarHecho")
  })
}

describe("el barrido está mirando algo", () => {
  it("descubre los modales del producto", () => {
    expect(MODALES.length).toBeGreaterThanOrEqual(30)
  })

  it("descubre archivos suficientes para resolver los importadores", () => {
    expect(TODOS.length).toBeGreaterThanOrEqual(300)
  })
})

describe("ningún alta se completa en silencio", () => {
  it("todo modal de formulario confirma cuando sale bien", () => {
    // 🔑 Se filtra sobre el PATH completo y el nombre sale al final. Buscar el path con
    // `endsWith(nombre)` daba el archivo equivocado —`EnviarPlantillaModal.tsx` termina en
    // "PlantillaModal.tsx" y `EditarNominaModal.tsx` en "NominaModal.tsx"—, así que dos modales
    // que SÍ avisaban salían reportados como mudos.
    const mudos = MODALES
      .filter((m) => !((m.split(/[\\/]/).pop() as string) in SIN_AVISO))
      .filter((m) => !avisa(m))
      .map((m) => m.split(/[\\/]/).pop() as string)
    expect(mudos,
      "Estos modales guardan y no dicen nada: el usuario se queda mirando la misma pantalla sin " +
      "saber si su click hizo algo. Usá `avisarGuardado`/`avisarHecho` " +
      "(`components/features/shared/avisoGuardado.ts`) o declaralo en SIN_AVISO con su razón.",
    ).toEqual([])
  })

  it("ninguna excepción declarada apunta a un modal que ya no existe", () => {
    const nombres = new Set(MODALES.map((m) => m.split(/[\\/]/).pop() as string))
    const muertas = Object.keys(SIN_AVISO).filter((n) => !nombres.has(n))
    expect(muertas, "Una excepción muerta es ruido que tapa el próximo caso.").toEqual([])
  })

  it("toda excepción tiene razón escrita", () => {
    const flacas = Object.entries(SIN_AVISO).filter(([, v]) => v.trim().length < 30)
    expect(flacas.map(([k]) => k)).toEqual([])
  })
})
