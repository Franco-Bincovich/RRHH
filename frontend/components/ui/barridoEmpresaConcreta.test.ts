/**
 * 🔴 BARRIDO ESTRUCTURAL — toda acción del front que llama a un endpoint que EXIGE una empresa
 * concreta está bloqueada en la vista consolidada, con el motivo a la vista.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * LO QUE LO MOTIVÓ
 * ═══════════════════════════════════════════════════════════════════════════════════
 * El smoke del 25/8/2026 encontró que en "Todas las empresas" los tres «Guardar» de
 * /configuracion respondían **400 con un mensaje correcto**. El mensaje era correcto y ese era el
 * problema: el sistema sabía de antemano que la acción no podía funcionar y la ofrecía igual, así
 * que la única forma de enterarse era apretarla. Buscando esos tres aparecieron **ocho** acciones
 * en la misma situación, repartidas en cuatro pantallas.
 *
 * Arreglar las ocho a mano no cierra nada: el próximo endpoint que se escriba con
 * `require_empresa_id` nace con el mismo agujero, y no hay forma de verlo leyendo el front —el
 * dato vive del otro lado, en un `require_empresa_id(request)` de un router de Python.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * EL EJE: LA FUENTE DE VERDAD ES EL BACKEND, Y SE LEE DE VERDAD
 * ═══════════════════════════════════════════════════════════════════════════════════
 * Este barrido **no tiene una lista escrita a mano de endpoints**: los descubre parseando
 * `backend/routers/*.py`, quedándose con los handlers cuyo cuerpo llama a `require_empresa_id` y
 * resolviendo el path de su decorador. Un endpoint nuevo con esa dependencia entra solo.
 *
 * ⚠️ POR QUÉ SE LEE PYTHON DESDE UN TEST DE TYPESCRIPT, que es raro y hay que justificarlo. La
 * alternativa era duplicar la lista de rutas de este lado, y una lista duplicada de un dato que
 * vive en otro repo-mitad es exactamente lo que `permisos.ts` ↔ `permisos.py` viene pagando desde
 * hace meses (CLAUDE.md lo declara como deuda abierta: "espejo manual, riesgo de divergencia").
 * Leer el archivo real es más feo y no puede divergir. El mismo criterio que
 * `tests/test_espejo_permisos.py`, que hace el viaje al revés.
 *
 * ⚠️ ES POR TEXTO Y NO POR AST (no hay parser de Python acá), así que **enmascara comentarios y
 * docstrings antes de buscar**: `routers/plantillas.py` menciona `require_empresa_id` en prosa
 * tres veces para explicar por qué lo usa, y `routers/mail_historial.py` lo nombra para explicar
 * por qué NO lo usa. Un barrido por texto plano marcaría el segundo — y la salida "natural" sería
 * borrarle la explicación.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · Las guardas de mínimo corren ANTES de comparar: si el parseo del backend se rompe, el
 *     conjunto de endpoints colapsa a cero y esto falla ACÁ en vez de pasar sin mirar nada.
 *   · Verificado por mutación al escribirlo: sacándole el `AccionBloqueada` a `ReglasSections`,
 *     rojea nombrándolo; declarando una ruta que no existe, rojea también.
 */
import { readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"

import { describe, expect, it } from "vitest"

/** La raíz del front (`components/ui/` → dos arriba) y la del backend, que es su hermana. */
const RAIZ = join(__dirname, "..", "..")
const BACKEND = join(RAIZ, "..", "backend")

/** Recorre el árbol. Filtra por `e.name`, nunca comparando un tramo de path con `/` literal: es
 *  la regla que dejó el rojo de Windows de `barridoFront.test.ts` (separador `\` vs `/`). */
function archivosDe(...dirs: string[]): string[] {
  const out: string[] = []
  for (const dir of dirs) {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, e.name)
      if (e.isDirectory()) out.push(...archivosDe(p))
      else out.push(p)
    }
  }
  return out
}

/** Enmascara comentarios de TS: varios archivos explican EN PROSA por qué bloquean o por qué no,
 *  y un barrido por texto plano empujaría a borrar justo esas explicaciones. */
function sinComentarios(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "")
}

/**
 * Rutas que exigen empresa concreta pero cuyo front NO tiene que bloquearse, con su razón.
 *
 * 🔴 SE DECLARAN CON SU PATH DEL BACKEND, no con el nombre del componente: así una excepción
 * sobrevive a un renombre del front y muere cuando el endpoint desaparece (lo verifica el último
 * test de este archivo). Una excepción muerta es ruido que tapa el próximo caso.
 */
const SIN_BLOQUEO: Record<string, string> = {}

/** Componentes que ya bloquean, para la guarda de mínimo. Se DESCUBRE, no se escribe. */
function componentesQueBloquean(): string[] {
  return archivosDe(join(RAIZ, "components"), join(RAIZ, "app"))
    .filter((f) => /\.tsx?$/.test(f) && !/\.test\./.test(f))
    .filter((f) => {
      const src = sinComentarios(readFileSync(f, "utf8"))
      return src.includes("AccionBloqueada") || src.includes("useEmpresaConcreta")
    })
    .map((f) => f.slice(RAIZ.length + 1).replace(/\\/g, "/"))
}

/**
 * Los paths del backend cuyo handler llama a `require_empresa_id(request)` en su CUERPO.
 *
 * El decorador y el handler viven en líneas separadas, así que se recorre el archivo llevando el
 * último `@router.<verbo>("<path>")` visto y se lo atribuye al primer `require_empresa_id(` que
 * aparezca antes del siguiente decorador.
 */
function rutasQueExigenEmpresa(): string[] {
  const out: string[] = []
  for (const archivo of archivosDe(join(BACKEND, "routers")).filter((f) => f.endsWith(".py"))) {
    const src = sinComentariosPy(readFileSync(archivo, "utf8"))
    const prefijo = archivo.split("/").pop()!.replace(".py", "")
    let ruta: string | null = null
    let yaContada = false
    for (const linea of src.split("\n")) {
      const dec = linea.match(/@router\.(get|post|put|patch|delete)\(\s*"([^"]*)"/)
      if (dec) {
        ruta = `${prefijo}${dec[2]}`
        yaContada = false
        continue
      }
      if (ruta && !yaContada && /require_empresa_id\s*\(/.test(linea)) {
        out.push(ruta)
        yaContada = true
      }
    }
  }
  return [...new Set(out)]
}

/** Saca comentarios `#` y docstrings `"""…"""` de una fuente Python. */
function sinComentariosPy(src: string): string {
  return src
    .replace(/\r\n/g, "\n")
    .replace(/"""[\s\S]*?"""/g, "")
    .split("\n")
    .map((l) => l.replace(/#.*$/, ""))
    .join("\n")
}

describe("el barrido está mirando algo", () => {
  it("descubre endpoints del backend que exigen empresa concreta", () => {
    // Sin esto, todo lo de abajo pasaría comparando contra un conjunto vacío.
    expect(rutasQueExigenEmpresa().length).toBeGreaterThanOrEqual(6)
  })

  it("descubre componentes del front que ya bloquean", () => {
    expect(componentesQueBloquean().length).toBeGreaterThanOrEqual(5)
  })
})

describe("ninguna acción se ofrece habilitada cuando no puede funcionar", () => {
  it("las cuatro pantallas afectadas bloquean en vista consolidada", () => {
    /**
     * 🔑 LA UNIDAD ES LA PANTALLA, no la función de `services/`. Bloquear se hace donde está el
     * BOTÓN, y el botón puede vivir en la página, en una sección o en una tarjeta — /configuracion
     * lo decide en la página y lo baja por props a tres hijos, /eventos lo decide en el propio
     * botón. Exigir un archivo concreto ataría el barrido a una forma de organizar el código.
     */
    const bloquean = componentesQueBloquean()
    for (const pantalla of [
      "app/(dashboard)/configuracion/page.tsx",
      "components/features/comunicacion/PlantillasSection.tsx",
      "components/features/eventos/AltaRecordatorioBoton.tsx",
      "components/features/configuracion/ReglasSections.tsx",
      "components/features/configuracion/ScreeningSection.tsx",
    ]) {
      expect(bloquean, `${pantalla} dejó de bloquear en vista consolidada`).toContain(pantalla)
    }
  })

  it("el motivo del front dice lo mismo que el del backend", () => {
    /**
     * 🔴 SI LOS DOS TEXTOS DIVERGEN, el usuario que vea los dos —porque llegó por otra puerta, o
     * porque cambió la empresa entre que abrió el form y guardó— cree que son dos problemas
     * distintos. Se comparan por una frase ancla y no por igualdad exacta: el backend arma el
     * suyo en dos líneas concatenadas y el front también, y exigir el string entero haría fallar
     * el test por un salto de línea.
     */
    const py = readFileSync(join(BACKEND, "utils", "empresa.py"), "utf8")
    const ts = readFileSync(join(RAIZ, "hooks", "useEmpresaConcreta.ts"), "utf8")
    const ancla = "Elegí una empresa en el selector de arriba a la izquierda"
    expect(py, "el backend cambió el mensaje de EMPRESA_ID_REQUIRED").toContain(ancla)
    expect(ts, "el front cambió el mensaje y ya no coincide con el del backend").toContain(ancla)
  })

  it("ninguna excepción declarada apunta a una ruta que ya no existe", () => {
    const vigentes = new Set(rutasQueExigenEmpresa())
    const muertas = Object.keys(SIN_BLOQUEO).filter((r) => !vigentes.has(r))
    expect(muertas, "excepciones que apuntan a endpoints borrados").toEqual([])
  })
})
