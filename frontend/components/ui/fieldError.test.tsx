/**
 * BARRIDO ESTRUCTURAL — el mensaje de error POR CAMPO lo pinta `FieldError` y mide 11px.
 *
 * 🔴 POR QUÉ. §3 dice 11px. El repo tenía el mensaje escrito a mano en 44 lugares con TRES
 * tamaños: `text-sm` (14px) en 8, `text-xs` (12px) en 32, y el 11px correcto sólo en los 4 del
 * modal de empleado. O sea que el mismo mensaje medía distinto según el formulario. Es el mismo
 * modo de falla que los 81 `<select>` con 29 constantes de estilo copiadas: una clase repetida
 * entre archivos diverge sola. Migrar los 44 sin dejar barrido no cierra nada — el campo nuevo
 * del próximo PR nace con `text-sm`.
 *
 * 🔑 EL EJE ES "MENSAJE DE UN CAMPO", NO "TEXTO ROJO". Se busca el patrón que renderiza
 * `errors.<campo>` / `errores.<campo>`, no cualquier `text-destructive`: los banners de
 * `serverError` y los avisos de fila son otra cosa y no miden 11px. Preguntar por el texto rojo
 * en general obligaría a declarar una excepción por cada aviso del producto, para siempre.
 */
import { readdirSync, readFileSync } from "node:fs"
import { join, resolve, sep } from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { FieldError } from "@/components/ui/FieldError"

const RAIZ = resolve(__dirname, "..", "..")

describe("el primitivo", () => {
  it("mide 11px y se anuncia", () => {
    const html = renderToStaticMarkup(<FieldError>Ingresá un CUIT de 11 dígitos</FieldError>)
    expect(html).toContain("text-[11px]")
    expect(html).toContain('role="alert"')
    expect(html).toContain("Ingresá un CUIT de 11 dígitos")
  })

  it("sin mensaje no pinta nada: el consumidor no necesita su propio condicional", () => {
    expect(renderToStaticMarkup(<FieldError>{""}</FieldError>)).toBe("")
    expect(renderToStaticMarkup(<FieldError>{undefined}</FieldError>)).toBe("")
  })

  it("acepta un id, para colgarlo del aria-describedby del campo", () => {
    expect(renderToStaticMarkup(<FieldError id="cuit-error">x</FieldError>)).toContain(
      'id="cuit-error"'
    )
  })
})

const IGNORAR = new Set(["node_modules"])

function archivosDe(carpeta: string): string[] {
  const salida: string[] = []
  const recorrer = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (IGNORAR.has(e.name) || e.name.startsWith(".")) continue
      const p = join(dir, e.name)
      if (e.isDirectory()) recorrer(p)
      // Los `.test.*` quedan afuera: este archivo escribe las clases que busca y se marcaría solo.
      else if (!e.name.includes(".test.") && /\.tsx$/.test(e.name)) {
        salida.push(p.slice(RAIZ.length + 1).split(sep).join("/"))
      }
    }
  }
  recorrer(join(RAIZ, carpeta))
  return salida
}

/** Enmascara comentarios: un archivo puede explicar la regla en prosa sin ser un uso. */
function sinComentarios(texto: string): string {
  return texto.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/\/\/.*/g, " ")
}

const ARCHIVOS = [...archivosDe("components"), ...archivosDe("app")]
const codigoDe = (rel: string) => sinComentarios(readFileSync(join(RAIZ, rel), "utf-8"))

/** Un `<p>`/`<span>` que pinta `errors.x` o `errores.x` sin pasar por el primitivo. */
const A_MANO = /<(?:p|span|div)\b[^>]*text-destructive[^>]*>\s*\{\s*(?:errors|errores)[.[]/

describe("barrido: nadie reimplementa el mensaje por campo", () => {
  it("guardas de mínimo", () => {
    expect(ARCHIVOS.length).toBeGreaterThanOrEqual(300)
    const consumidores = ARCHIVOS.filter((f) => codigoDe(f).includes("<FieldError"))
    expect(consumidores.length).toBeGreaterThanOrEqual(15)
  })

  it("ningún archivo escribe el mensaje de un campo a mano", () => {
    const rotos = ARCHIVOS.filter((f) => A_MANO.test(codigoDe(f)))
    expect(
      rotos,
      "usá `<FieldError>{errors.campo}</FieldError>`: §3 pide 11px y el tamaño lo decide el " +
        "primitivo, no cada formulario"
    ).toEqual([])
  })

  it("todo archivo que pinta <FieldError> lo importa del primitivo", () => {
    // Sin esto, un `FieldError` local esquivaría la aserción de arriba con el mismo nombre.
    const rotos = ARCHIVOS.filter((f) => {
      const codigo = codigoDe(f)
      return (
        codigo.includes("<FieldError") &&
        !codigo.includes('from "@/components/ui/FieldError"') &&
        !f.endsWith("components/ui/FieldError.tsx")
      )
    })
    expect(rotos).toEqual([])
  })

  it("el detector reconoce el patrón a mano (si no, el barrido no prueba nada)", () => {
    expect(A_MANO.test('<p className="text-xs text-destructive">{errors.nombre}</p>')).toBe(true)
    expect(A_MANO.test('<p className="text-sm text-destructive">{errores.fecha}</p>')).toBe(true)
    expect(A_MANO.test("<FieldError>{errors.nombre}</FieldError>")).toBe(false)
    // Un banner de formulario NO es un mensaje de campo y no tiene que marcarse.
    expect(A_MANO.test('<p className="mt-2 text-sm text-destructive">{serverError}</p>')).toBe(false)
  })
})
