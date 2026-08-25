import { readdirSync, readFileSync } from "node:fs"
import { dirname, join, resolve, sep } from "node:path"

import { describe, expect, it } from "vitest"

/**
 * 🔴 BARRIDO ESTRUCTURAL — **toda acción que BORRA pasa por `<ConfirmDialog>`.**
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * EL BUG QUE CIERRA
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * Hasta el 24/8/2026 había CINCO pantallas donde un click destruía un dato y no había ningún
 * paso entre el puntero y la pérdida: /ausencias (Eliminar), /vacaciones (Cancelar), /periodos
 * (Cerrar período), /inventario (Eliminar) y /objetivos (Eliminar). El patrón canónico ya
 * existía —`ConfirmDialog`, usado en /areas y /usuarios— y lo usaban 8 componentes de todo el
 * front, así que no era una decisión: era que nadie lo había cableado.
 *
 * La peor era /objetivos: la FK `parent_id` es ON DELETE CASCADE, o sea que ese click se llevaba
 * el objetivo Y todos sus subobjetivos sin nombrarlos en ningún lado. En esa ventana desapareció
 * un objetivo real de Karstec.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * EL EJE, Y POR QUÉ ESTE
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * **Una función de `services/` que hace `method: "DELETE"`.** No "un botón que dice Eliminar"
 * ni "un handler que se llama handleDelete": esos son texto y convención, y el barrido se
 * esquiva sin querer con sólo renombrar. El verbo HTTP es el hecho — del otro lado hay una fila
 * que deja de existir.
 *
 * Medido al escribirlo: **21 funciones** en `services/` hacen DELETE, y el descubrimiento es por
 * lectura del árbol, así que **la número 22 entra sola**. Ese es el punto: el próximo módulo con
 * borrado no puede nacer sin diálogo y en verde.
 *
 * 🔑 **LA UNIDAD ES EL ARCHIVO MÁS SUS IMPORTADORES DIRECTOS — UN SALTO.** Hace falta al menos
 * uno porque el que LLAMA a `deleteObjetivo` es `useAccionesObjetivos` (un hook, que no renderiza
 * nada) y el que monta el diálogo es la página. Y **no más de uno, y está medido**: con el cierre
 * transitivo —que es lo que hace `barridoPaginacion`, y ahí es correcto porque su pregunta es de
 * PANTALLA— este barrido daba falsos VERDES. `AdjuntosSection` borra un adjunto con el `confirm()`
 * del navegador y pasaba, porque tres saltos más arriba estaba `ausencias/page.tsx` montando un
 * ConfirmDialog **para otra acción**. La pregunta acá es de ACCIÓN, no de pantalla.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
 *   · No hay lista escrita a mano de qué mirar: ni de funciones destructivas ni de pantallas.
 *     Lo único a mano son las EXCEPCIONES, y la contracara de abajo las mata cuando dejan de
 *     corresponder.
 *   · Verificado por mutación en las dos direcciones al escribirlo: sacándole el
 *     `<ConfirmDialog>` a `app/(dashboard)/ausencias/page.tsx` rojea nombrando la pantalla; con
 *     él puesto, verde. Y sacando una excepción declarada, también rojea.
 *   · Las guardas de mínimo corren ANTES de comparar: si el recorrido del árbol o el grafo de
 *     imports se rompieran, cada unidad quedaría en un solo archivo, nadie montaría el diálogo y
 *     "no hay infractores" pasaría **sin haber mirado una sola pantalla**. Es el falso verde que
 *     este repo ya pagó con `barridoFront.test.ts`, que en Windows descubría 0 exports y pasaba.
 *
 * 🔑 **LOS COMENTARIOS SE ENMASCARAN.** Varios de los archivos migrados explican EN PROSA por
 * qué su acción NO es un borrado (cancelar unas vacaciones, cerrar un período) y `useAccionesPerfil`
 * explica por qué reactivar no lleva diálogo. Un barrido por texto plano los contaría como si
 * montaran el componente, y de paso empujaría a borrar justo esas explicaciones. Hay un test
 * abajo que fija que la prosa no cuenta.
 */

const RAIZ = resolve(__dirname, "..", "..")
const CARPETAS = ["app", "components", "hooks", "services"]

/**
 * Acciones que NO son un `DELETE` de HTTP y aun así se decidió que pidan confirmación.
 *
 * 🔴 SON DOS Y LAS DOS SON DEL 24/8/2026. El eje del barrido es el verbo HTTP porque es un hecho
 * y no una convención, pero eso deja afuera dos acciones que el usuario vive como destructivas
 * aunque técnicamente sean un UPDATE. Se declaran acá para que el barrido las vigile igual: si
 * alguien les saca el diálogo, esto rojea.
 *
 * ⚠️ Y son las dos cuyo TEXTO no puede decir "eliminar" — ver la regla 2 de
 * `components/features/shared/confirmaciones.ts`.
 */
const CONFIRMAN_SIN_SER_DELETE: Record<string, string> = {
  cancelarVacacion:
    "No borra: setea `cancelada=true`. La fila sigue en el listado y los días vuelven al saldo " +
    "(el cálculo filtra por `cancelada=false`). Pide confirmación igual porque el botón está en " +
    "la fila, al lado del de adjuntos, y deshacerlo exige volver a cargar la solicitud entera.",
  cerrarPeriodo:
    "No borra y es REVERSIBLE (la misma pantalla tiene Reabrir), pero le pone un candado a un " +
    "rango de fechas para toda la empresa: nadie puede cargar, editar ni borrar ahí adentro. " +
    "Era un submit de formulario, que es el gesto más automático de la pantalla.",
}

/**
 * Llamadores de una función destructiva que hoy NO montan `ConfirmDialog`, con su razón y su
 * clase. La contracara de abajo las mata solas cuando el motivo desaparece.
 *
 * 🔴 ESTAS DIEZ LAS ENCONTRÓ EL BARRIDO, NO UNA REVISIÓN. La tanda del 24/8/2026 entró a
 * arreglar CINCO pantallas sin confirmación —las que se habían visto a ojo— y este archivo, la
 * primera vez que corrió, devolvió DIEZ MÁS. Ese es el argumento entero a favor de tenerlo: la
 * revisión a mano encontró la mitad.
 *
 * SON TRES CLASES DISTINTAS y no hay que leerlas igual:
 *   · **BESPOKE** — confirman, con un diálogo propio en vez del canónico. No hay bug para el
 *     usuario; hay dos implementaciones del mismo diálogo.
 *   · **NATIVO** — confirman con el `confirm()` del navegador. Hay un bug menor de producto (esa
 *     caja no se estila, ignora el tema y en mobile aparece pegada a la barra con la URL del
 *     sitio arriba) y hay inconsistencia con el resto. Ver también la regla de abajo.
 *   · **🔴 SIN CONFIRMACIÓN** — un click y el dato se va. Es el mismo agujero que esta tanda
 *     vino a cerrar, en cinco pantallas más. Se declaran en vez de taparlas: arreglarlas exige
 *     decidir el TEXTO de cada una (qué se pierde exactamente), y eso es una tanda propia con
 *     este archivo como lista de tareas.
 */
const EXCEPCIONES: Record<string, string> = {
  // ── BESPOKE: confirman con su propio diálogo ───────────────────────────────
  "components/features/areas/useAreasAcciones.ts":
    "BESPOKE. /areas SÍ confirma, con `AreaEliminarDialog` — de hecho es el molde de copy que " +
    "esta tanda copió ('¿…querés eliminar ADMINISTRACION? Esta acción no se puede deshacer'). " +
    "Ese componente existe porque una división anterior tenía que ser un movimiento puro y su " +
    "propio docstring dice que unificarlo con ConfirmDialog es una tarea aparte. 🚩 Salida: " +
    "cuando se unifique, borrar esta entrada Y el componente (55 líneas duplicadas).",
  "components/features/empresas/EmpresaAreasTab.tsx":
    "BESPOKE. Confirma con un `<Dialog>` escrito a mano adentro del propio tab (línea ~184), " +
    "que es una TERCERA copia del mismo diálogo de 'Eliminar área' — la misma acción que " +
    "/areas, con dos implementaciones distintas. 🚩 Salida: la misma unificación de arriba.",

  // ── NATIVO: confirman con la caja del navegador ────────────────────────────
  "components/features/adjuntos/AdjuntosSection.tsx":
    "NATIVO. Borra un adjunto con `confirm()` del navegador. 🔴 Es el que descubrió que la " +
    "unidad no podía ser transitiva: pasaba en verde colgado del ConfirmDialog de la pantalla " +
    "que lo contiene, que confirma otra cosa.",
  "components/features/proyectos/EquipoTab.tsx":
    "NATIVO. Quitar a alguien de un proyecto, con `confirm()`. ⚠️ Puede chocar con " +
    "ASIGNACION_CON_HORAS (409) si la persona tiene horas cargadas, así que el texto tendría " +
    "algo real que decir.",
  "components/features/proyectos/HorasTab.tsx":
    "NATIVO. Borra una carga de horas del proyecto con `confirm()`. 🔴 Es la MISMA acción que " +
    "`horasCliente/DetalleEmpleadoModal`, que no confirma nada: el mismo dato —el que factura— " +
    "se borra de dos formas distintas según por qué pantalla se entre. 🔑 Lo cazó la regla del " +
    "`confirm()` nativo y no el eje principal, porque `deleteHora` es un `export function` sin " +
    "`async` y el detector pedía `export async function`. El detector se arregló; la entrada " +
    "queda como registro de que las dos reglas se cubren mutuamente.",
  "components/features/vacantes/VacanteImagenes.tsx":
    "NATIVO. Borra una imagen de la vacante con `confirm()`.",

  // ── 🔴 SIN CONFIRMACIÓN: un click y el dato se va ──────────────────────────
  "components/features/capacitaciones/AsignacionesTab.tsx":
    "🔴 SIN CONFIRMACIÓN. Desasignar una formación a una persona: se pierde que la tuvo " +
    "asignada, con su estado y su certificado. Y el backend TAMPOCO lo audita (ver " +
    "`tests/test_auditoria_destructivas.py`), así que no queda rastro por ningún lado.",
  "components/features/capacitaciones/CatalogoTab.tsx":
    "🔴 SIN CONFIRMACIÓN. Borra un curso del catálogo de un click. Sin auditoría del lado del " +
    "backend tampoco.",
  "components/features/comunicacion/usePlantillas.ts":
    "🔴 SIN CONFIRMACIÓN. Borra una plantilla de mail: el Markdown que RRHH escribió desaparece " +
    "y no hay versión anterior de la que sacarlo. Sin auditoría del lado del backend tampoco.",
  "components/features/configuracion/accionesIntegracion.ts":
    "🔴 SIN CONFIRMACIÓN. Desconecta una integración (Gmail, Anthropic, Zernio) borrando la " +
    "credencial. Desconectar la casilla del sistema deja de mandar TODOS los mails del " +
    "producto, y es un click sin pregunta.",
  "components/features/horasCliente/DetalleEmpleadoModal.tsx":
    "🔴 SIN CONFIRMACIÓN, y es la peor de las cinco: borra una CARGA DE HORAS, que es el dato " +
    "que factura. Editar una carga no existe a propósito (la carga es irreversible por decisión " +
    "de producto), o sea que este borrado es la única forma de cambiar una hora ya cargada — y " +
    "no pregunta nada ni deja evento de auditoría.",
}

// ─────────────────────────────────────────────────────────────────────────────

/** Saca comentarios de línea y de bloque sin romper los strings. Ver el 🔑 del encabezado. */
function sinComentarios(src: string): string {
  const texto = src.replace(/\r\n/g, "\n")
  let out = ""
  for (let i = 0; i < texto.length;) {
    const dos = texto.slice(i, i + 2)
    if (dos === "/*") {
      const fin = texto.indexOf("*/", i + 2)
      i = fin < 0 ? texto.length : fin + 2
      continue
    }
    if (dos === "//") {
      const fin = texto.indexOf("\n", i)
      i = fin < 0 ? texto.length : fin
      continue
    }
    const c = texto[i]
    if (c === '"' || c === "'" || c === "`") {
      let j = i + 1
      while (j < texto.length && texto[j] !== c) j += texto[j] === "\\" ? 2 : 1
      out += texto.slice(i, j + 1)
      i = j + 1
      continue
    }
    out += c
    i += 1
  }
  return out
}

function archivosDe(carpeta: string): string[] {
  const salida: string[] = []
  const recorrer = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (e.name === "node_modules" || e.name.startsWith(".")) continue
      const p = join(dir, e.name)
      if (e.isDirectory()) recorrer(p)
      // 🔑 Los `.test.*` quedan FUERA del grafo. Si entraran, el `*Patron.test.tsx` de cada
      // pantalla le "montaría" su propio ConfirmDialog y el barrido no podría marcar a nadie.
      else if (/\.tsx?$/.test(e.name) && !/\.test\./.test(e.name)) {
        // Normalizado a "/" en el único lugar donde nacen los paths: en Windows `join` usa "\"
        // y comparar un tramo con "/" literal descubre CERO archivos y pasa en verde. Es el
        // cuarto rojo de Windows que este repo se comió.
        salida.push(p.slice(RAIZ.length + 1).split(sep).join("/"))
      }
    }
  }
  recorrer(join(RAIZ, carpeta))
  return salida
}

const ARCHIVOS = CARPETAS.flatMap(archivosDe)
const EXISTE = new Set(ARCHIVOS)
const CODIGO = new Map(ARCHIVOS.map((f) => [f, sinComentarios(readFileSync(join(RAIZ, f), "utf-8"))]))
const codigo = (f: string) => CODIGO.get(f) ?? ""

/** Un import del repo → su ruta, o `null` si apunta afuera (node_modules, `@/types`…). */
function destino(desde: string, spec: string): string | null {
  const base = spec.startsWith("@/") ? spec.slice(2)
    : spec.startsWith(".") ? join(dirname(desde), spec).split(sep).join("/")
      : null
  if (!base) return null
  for (const c of [`${base}.tsx`, `${base}.ts`, `${base}/index.tsx`, `${base}/index.ts`]) {
    if (EXISTE.has(c)) return c
  }
  return null
}

const IMPORTADORES = new Map<string, Set<string>>()
for (const f of ARCHIVOS) {
  for (const m of codigo(f).matchAll(/from\s+"([^"]+)"/g)) {
    const t = destino(f, m[1])
    if (t) {
      if (!IMPORTADORES.has(t)) IMPORTADORES.set(t, new Set())
      IMPORTADORES.get(t)!.add(f)
    }
  }
}

/**
 * El archivo más los que lo importan DIRECTAMENTE — un solo salto, no el cierre transitivo.
 *
 * 🔴 UN SALTO Y NO TODOS, Y ESTÁ MEDIDO. Con el cierre transitivo (que es lo que hace
 * , y ahí es correcto porque su pregunta es de PANTALLA) este barrido daba
 * falsos VERDES:  —que borra un adjunto sin confirmar— pasaba porque tres
 * saltos más arriba estaba , que monta un ConfirmDialog **para otra acción**.
 * La pregunta acá es de ACCIÓN, no de pantalla: el diálogo se monta donde se dispara, o en el
 * componente que la cablea. Más arriba ya es otra cosa que confirma otra cosa.
 */
function unidad(archivo: string): string[] {
  return [archivo, ...(IMPORTADORES.get(archivo) ?? [])]
}

// ── Las funciones destructivas, descubiertas leyendo `services/` ──────────────
/**
 * `export [async] function X(...)` cuyo cuerpo hace `method: "DELETE"`.
 *
 * 🔑 EL `async` ES OPCIONAL EN EL PATRÓN, y no es un detalle: la primera versión exigía
 * `export async function` y se comió `deleteHora` (`services/proyectos.ts:134`), que devuelve
 * la promesa sin declararse async. Lo cazó la regla del `confirm()` nativo, de abajo — o sea
 * que las dos reglas se cubren mutuamente, que es la razón por la que conviven acá.
 */
const DESTRUCTIVAS: string[] = []
for (const f of ARCHIVOS.filter((a) => a.startsWith("services/"))) {
  const src = codigo(f)
  for (const m of src.matchAll(/export (?:async )?function (\w+)\s*\(/g)) {
    const desde = m.index! + m[0].length
    const fin = src.indexOf("\nexport ", desde)
    if (src.slice(desde, fin < 0 ? undefined : fin).includes('method: "DELETE"')) {
      DESTRUCTIVAS.push(m[1])
    }
  }
}
const VIGILADAS = [...DESTRUCTIVAS, ...Object.keys(CONFIRMAN_SIN_SER_DELETE)]

/** Quién IMPORTA una función vigilada desde fuera de `services/` (o sea: quién la usa). */
const LLAMADORES = ARCHIVOS.filter(
  (f) => !f.startsWith("services/")
    && VIGILADAS.some((fn) => new RegExp(`\\b${fn}\\b`).test(codigo(f))),
)

const montaDialogo = (f: string) => /<ConfirmDialog\b/.test(codigo(f))
const INFRACTORES = LLAMADORES.filter(
  (f) => !unidad(f).some(montaDialogo) && !(f in EXCEPCIONES),
)

// ─────────────────────────────────────────────────────────────────────────────

describe("Barrido: toda acción que borra pasa por ConfirmDialog", () => {
  it("descubre las funciones destructivas de services/", () => {
    // Guarda contra el falso verde: si la detección del verbo se rompiera, DESTRUCTIVAS quedaría
    // vacío, no habría llamadores y "no hay infractores" pasaría sin haber mirado nada.
    expect(DESTRUCTIVAS.length).toBeGreaterThanOrEqual(16)
  })

  it("descubre los archivos y el grafo de imports", () => {
    expect(ARCHIVOS.length).toBeGreaterThanOrEqual(300)
    expect(LLAMADORES.length).toBeGreaterThanOrEqual(15)
  })

  it("hay unidades que YA montan el diálogo (si no, el grafo está roto)", () => {
    // La guarda que más rinde: es la única que ve un grafo de imports que dejó de resolver.
    const conDialogo = LLAMADORES.filter((f) => unidad(f).some(montaDialogo))
    expect(conDialogo.length).toBeGreaterThanOrEqual(10)
  })

  it("ninguna acción destructiva llega al backend sin confirmación", () => {
    expect(INFRACTORES).toEqual([])
  })

  it("las excepciones declaradas siguen correspondiendo", () => {
    // Una excepción que apunta a un archivo borrado —o que ya montó el diálogo— es ruido que
    // tapa el próximo caso.
    for (const archivo of Object.keys(EXCEPCIONES)) {
      expect(EXISTE.has(archivo), `${archivo} ya no existe`).toBe(true)
      expect(unidad(archivo).some(montaDialogo), `${archivo} ya monta el diálogo`).toBe(false)
    }
  })

  it("toda excepción tiene su razón escrita", () => {
    for (const [archivo, razon] of Object.entries(EXCEPCIONES)) {
      expect(razon.trim().length, `${archivo} sin razón`).toBeGreaterThan(40)
    }
    for (const [fn, razon] of Object.entries(CONFIRMAN_SIN_SER_DELETE)) {
      expect(razon.trim().length, `${fn} sin razón`).toBeGreaterThan(40)
    }
  })

  it("las dos que confirman sin ser DELETE existen y no son DELETE", () => {
    // Si alguna pasara a ser un DELETE de verdad, entraría sola por el eje principal y su
    // declaración acá se volvería ruido.
    for (const fn of Object.keys(CONFIRMAN_SIN_SER_DELETE)) {
      expect(DESTRUCTIVAS, `${fn} ya es un DELETE: sacalo de la lista`).not.toContain(fn)
      expect(ARCHIVOS.some((f) => f.startsWith("services/") && new RegExp(`function ${fn}\\b`).test(codigo(f))),
        `${fn} no existe en services/`).toBe(true)
    }
  })

  it("nadie confirma con el confirm() del navegador salvo los declarados", () => {
    /* 🔴 REGLA APARTE, Y NO REDUNDANTE CON LA DE ARRIBA. Un `confirm()` nativo SÍ frena al
       usuario, así que no es el mismo bug que no preguntar nada — pero es una caja que no se
       puede estilar, que ignora el tema y que en mobile aparece pegada a la barra del navegador
       con la URL del sitio arriba. Y sobre todo: convive con `ConfirmDialog` en el mismo
       producto, así que la misma acción se ve de dos formas según la pantalla.
       /periodos tenía las dos a la vez —cerrar sin preguntar nada y reabrir con la caja gris del
       sistema— y esta tanda lo dejó con las dos en `ConfirmDialog`. */
    const nativos = ARCHIVOS.filter((f) => /(?<![.\w])confirm\s*\(/.test(codigo(f)))
    const nuevos = nativos.filter((f) => !(f in EXCEPCIONES))
    expect(nuevos, "usan confirm() del navegador y no están declarados").toEqual([])
    // Contracara: si alguno se migró, su declaración de arriba tiene que dejar de decir NATIVO.
    for (const f of Object.keys(EXCEPCIONES)) {
      if (EXCEPCIONES[f].startsWith("NATIVO")) {
        expect(nativos, `${f} ya no usa confirm(): actualizá su declaración`).toContain(f)
      }
    }
  })

  it("la prosa NO cuenta como montar el diálogo", () => {
    // Sin esto, un archivo que MENCIONE ConfirmDialog en un comentario —explicando por qué ahí
    // no hace falta— pasaría el barrido sin montarlo.
    expect(sinComentarios('// <ConfirmDialog />\nconst a = 1')).not.toContain("ConfirmDialog")
    expect(sinComentarios('/* <ConfirmDialog /> */\nconst a = 1')).not.toContain("ConfirmDialog")
    expect(sinComentarios('const s = "<ConfirmDialog />"')).toContain("ConfirmDialog")
  })
})
