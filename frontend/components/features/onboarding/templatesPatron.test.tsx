import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { TemplatesList } from "./TemplatesList"

/**
 * El patrón del bloque B sobre /onboarding/templates. La pantalla hermana —/onboarding— tiene su
 * propio archivo (`onboardingPatron.test.tsx`).
 *
 * ⚠️ (a) (b) y (d) NO APLICAN, y no es un olvido: `GET /api/onboarding/templates` no acepta un
 * solo Query — devuelve la lista entera. Sin filtros no hay chips y sin paginado no hay pie.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (c) que el vacío vuelva a la frase genérica y deje de decir qué se pierde sin templates.
 *   · que el error vuelva a dibujarse como un vacío, sin reintento.
 *   · que el ámbar crudo vuelva a la tarjeta del template sin empresa.
 *   · que el alta vuelva a ser un `<button>` con `bg-primary` escrito a mano.
 */

function templates(props: Partial<Parameters<typeof TemplatesList>[0]> = {}) {
  return renderToStaticMarkup(
    <TemplatesList
      templates={[]} loading={false} error={null} canWrite={false} mostrarEmpresa={false}
      deletingId={null} onAbrir={() => {}} onEliminar={() => {}} onReintentar={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío dice lo que la AUSENCIA significa, no sólo que no hay nada", () => {
  it("sin templates, la consecuencia es que no se puede iniciar ningún onboarding", () => {
    /*
     * La frase genérica de `textoVacio` —"cuando se cargue el primero va a aparecer acá"— es
     * cierta y no sirve: lo que el usuario necesita saber es que el template NO es un adorno, es
     * el requisito para arrancar un proceso. Sin ninguno, el botón de la otra pantalla no tiene
     * de dónde copiar el checklist.
     */
    const html = templates()
    expect(html).toContain("Todavía no hay ningún template")
    expect(html).toContain("no se puede iniciar un onboarding")
  })

  it("🔴 el error NO se dibuja como un vacío: trae su reintento", () => {
    const html = templates({ error: "No se pudieron cargar los templates" })
    expect(html).toContain("Reintentar")
    expect(html).toContain("No se pudieron cargar los templates")
    // Y no afirma que no haya templates cuando lo que hubo fue una falla.
    expect(html).not.toContain("Todavía no hay ningún template")
  })

  it("el esqueleto tiene la forma de las tarjetas que van a llegar, con shimmer", () => {
    const html = templates({ loading: true })
    expect(html).toContain("animate-shimmer")
    expect(html).toContain("h-20")
    // Guarda: si el esqueleto se cayera, el vacío ocuparía su lugar y esto lo caza.
    expect(html).not.toContain("Todavía no hay ningún template")
  })

  it("la acción del vacío sólo aparece con permiso de escritura", () => {
    const conAlta = templates({ accionVacio: <button type="button">Nuevo template</button> })
    expect(conAlta).toContain("Nuevo template")
    // Sin `accionVacio` —que es lo que la página pasa sin permiso— el vacío no ofrece nada.
    expect(templates()).not.toContain("Nuevo template")
  })
})

describe("🔴 el ámbar crudo salió de la tarjeta", () => {
  it("el aviso del template global usa el par `warning` de la paleta, no `amber-*`", () => {
    /*
     * Era `border-amber-200 bg-amber-50 text-amber-800` escrito a mano: seis valores elegidos de
     * la escala de Tailwind, que el barrido de contraste (`app/contrasteTokens.test.ts`) no mide
     * y que un ajuste de la paleta deja atrás. El par semántico ya trae su valor de modo oscuro.
     */
    const src = readFileSync(path.resolve(__dirname, "TemplatesList.tsx"), "utf8")
    expect(src).toContain("border-warning-line")
    expect(src).toContain("bg-warning-wash")
    expect(src).toContain("text-warning")
    expect(sinComentarios(src)).not.toContain("amber-")
  })

  it("y la fila entera reacciona al apuntar, en vez de revelar el chevron", () => {
    // §3: las acciones están SIEMPRE a la vista; lo que hace el hover es subir el contraste.
    const src = readFileSync(path.resolve(__dirname, "TemplatesList.tsx"), "utf8")
    expect(src).toContain("group-hover:text-primary")
  })
})

/** El código sin comentarios. Los finales de Windows se normalizan ANTES de nada: con `\r\n`
 *  cada línea termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("la página: el alta sale del primitivo y el reintento vuelve a cargar", () => {
  const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "onboarding", "templates", "page.tsx")

  it("🔴 el botón de alta es <Button>, no un <button> con `bg-primary` a mano", () => {
    /*
     * Escrito a mano se pierden el alto mínimo de 44px del sistema, el anillo de foco visible y
     * el estado deshabilitado — tres cosas que nadie va a reponer copiando clases.
     */
    const src = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(src).toContain("const nuevoBtn = (")
    expect(src).toContain("<Button")
    expect(src).not.toMatch(/<button[^>]*bg-primary/)
  })

  it("la carga sale del efecto para que el reintento y el vacío la puedan disparar", () => {
    const src = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(src).toContain("useCallback")
    expect(src).toContain("onReintentar={cargar}")
  })

  it("⚠️ y no monta filtros ni pie, que es lo correcto para esta lista", () => {
    const src = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(src).not.toContain("<FiltersBar")
    expect(src).not.toContain("<Pagination")
  })
})
