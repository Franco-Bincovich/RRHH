import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { OnboardingList } from "./OnboardingList"

/**
 * El patrón del bloque B sobre /onboarding. La pantalla hermana —/onboarding/templates, que vive
 * en este mismo módulo— tiene su propio archivo (`templatesPatron.test.tsx`): son dos pantallas,
 * y el criterio del repo es un archivo de test por módulo, partido cuando cubre dos cosas.
 *
 * ⚠️ (a) (b) y (d) NO APLICAN, y no es un olvido: `GET /api/onboarding/instancias` no acepta un
 * solo Query — devuelve la lista entera. Sin filtros no hay chips y sin paginado no hay pie.
 * Hay un test abajo que lo fija.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (c) que el vacío vuelva a la frase genérica y deje de decir qué significa la ausencia.
 *   · que el error vuelva a dibujarse como un vacío, sin reintento.
 *   · que el esqueleto vuelva al `animate-pulse` de 2s en vez del shimmer del patrón.
 *   · que el modal de alta vuelva a ser un `<div fixed inset-0>` escrito a mano.
 */

type Instancia = Parameters<typeof OnboardingList>[0]["onboardings"][number]

const INSTANCIA = {
  id: "i1", empleado_id: "e1", empleado_nombre: "Ana Gómez", empleado_cargo: "Analista",
  empleado_area: "Sistemas", empresa_nombre: "Karstec", progreso: 40,
  tareas_completadas: 2, tareas_total: 5,
} as unknown as Instancia

describe("la lista de procesos en curso", () => {
  it("cada fila es un botón que abre el detalle de ESA persona", () => {
    const html = renderToStaticMarkup(
      <OnboardingList onboardings={[INSTANCIA]} mostrarEmpresa={false} deshabilitado={false} onAbrir={() => {}} />,
    )
    expect(html).toContain("Ana Gómez")
    expect(html).toContain("Analista")
  })

  it("mientras se trae un detalle, no se puede abrir otro", () => {
    // Sin esto, dos clics seguidos disparan dos cargas y gana la que vuelva última, que puede no
    // ser la que el usuario apretó al final.
    const html = renderToStaticMarkup(
      <OnboardingList onboardings={[INSTANCIA]} mostrarEmpresa={false} deshabilitado onAbrir={() => {}} />,
    )
    expect(html).toContain("disabled")
  })

  it("la empresa se marca SÓLO en modo consolidado", () => {
    const solo = renderToStaticMarkup(
      <OnboardingList onboardings={[INSTANCIA]} mostrarEmpresa={false} deshabilitado={false} onAbrir={() => {}} />,
    )
    const consolidado = renderToStaticMarkup(
      <OnboardingList onboardings={[INSTANCIA]} mostrarEmpresa deshabilitado={false} onAbrir={() => {}} />,
    )
    expect(solo).not.toContain("Karstec")
    expect(consolidado).toContain("Karstec")
  })
})

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("🔴 el modal de alta salió del diálogo escrito a mano", () => {
  const MODAL = path.resolve(__dirname, "IniciarOnboardingModal.tsx")

  it("usa el primitivo con `patron=\"formulario\"`, no un scrim propio", () => {
    /*
     * Tenía su propio `<div className="fixed inset-0 z-50 bg-black/40">`, su `role="dialog"` y sus
     * botones con `bg-primary` a mano: una reimplementación parcial del primitivo SIN lo que el
     * primitivo resuelve —foco atrapado, cierre con Escape, alto en `dvh`—.
     */
    const src = sinComentarios(readFileSync(MODAL, "utf8"))
    expect(src).toContain('<DialogContent patron="formulario">')
    expect(src).toContain("<DialogDescription>")
    expect(src).not.toContain("fixed inset-0")
    expect(src).not.toContain('role="dialog"')
  })

  it("⚠️ y NO tiene banner de errores, porque tampoco tiene mensajes por campo", () => {
    // Un `<FormErrores cantidad>` arriba diría "Revisá 0 campos" siempre: hay un único error de
    // servidor abajo y el botón deshabilitado hasta que haya persona y template.
    expect(sinComentarios(readFileSync(MODAL, "utf8"))).not.toContain("<FormErrores")
    // El único error vive con los campos, que salieron a su propio archivo por el límite de 150.
    const campos = sinComentarios(readFileSync(path.resolve(__dirname, "IniciarOnboardingFields.tsx"), "utf8"))
    expect(campos).toContain('role="alert"')
    expect(campos).not.toContain("<FormErrores")
  })
})

describe("⚠️ (a) (b) y (d) no aplican: ninguna de las dos pantallas filtra ni pagina", () => {
  it("la lista no monta FiltersBar ni Pagination", () => {
    for (const archivo of ["OnboardingList.tsx"]) {
      const src = sinComentarios(readFileSync(path.resolve(__dirname, archivo), "utf8"))
      expect(src, `${archivo} montó una barra de filtros que el backend no puede honrar`).not.toContain("<FiltersBar")
      expect(src, `${archivo} montó un pie sin backend paginado`).not.toContain("<Pagination")
    }
  })
})
