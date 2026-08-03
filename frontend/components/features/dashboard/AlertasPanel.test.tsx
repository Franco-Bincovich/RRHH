import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import type { AlertaDashboard } from "@/services/dashboard"

/**
 * La card de alertas del dashboard: contador en el encabezado y contenido plegable.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. El contador NO se lee buscando el número suelto en el markup: se extrae del chip que va
 *    pegado al <h2> del encabezado. Un `toContain("7")` pasaría con el contador borrado, porque
 *    el 7 aparece igual en cualquier clase de Tailwind o en el texto de una alerta — sería el
 *    caso #5 del CLAUDE.md (aserción vacua en verde). El helper devuelve null si esa estructura
 *    no existe, y cada test lo afirma explícitamente antes de comparar.
 * 2. Los mensajes de las alertas NO traen dígitos, para que ningún número del contenido pueda
 *    hacer pasar una aserción sobre el contador por casualidad.
 * 3. El acordeón es el real de base-ui, sin mockear: un panel plegado NO renderiza su contenido
 *    (verificado en ConfigSection.test.tsx), así que "arranca abierta" es afirmable — si alguien
 *    le saca el `defaultValue`, los mensajes desaparecen del markup y rojea.
 *
 * Sin jsdom no hay click: el eje abierto/cerrado se cubre en ConfigSection.test.tsx, que es
 * donde vive el mecanismo. Acá se verifica el estado INICIAL, que es la decisión de esta card.
 */

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
}))

const { AlertasPanel } = await import("./AlertasPanel")

/** El chip que va inmediatamente después del título dentro del trigger. null si no está. */
function contador(html: string): string | null {
  const m = html.match(/<h2[^>]*>Alertas activas<\/h2><span[^>]*>([^<]*)<\/span>/)
  return m ? m[1] : null
}

function alertas(n: number): AlertaDashboard[] {
  return Array.from({ length: n }, (_, i) => ({
    tipo: "dato_faltante",
    // Sin dígitos a propósito: ver el punto 2 del encabezado.
    mensaje: `Empleado sin manager asignado ${"·".repeat(i + 1)}`,
    nivel: "warning" as const,
    href: null,
  }))
}

const render = (n: number) => renderToStaticMarkup(<AlertasPanel alertas={alertas(n)} />)

describe("contador de alertas", () => {
  it("coincide con la cantidad real", () => {
    for (const n of [1, 3, 7, 12]) {
      expect(contador(render(n))).toBe(String(n))
    }
  })

  it("con cero alertas muestra 0, no se esconde", () => {
    // "0" es una respuesta legítima a cuántas alertas hay. Un chip que desaparece obliga a
    // distinguir "sin alertas" de "el contador se rompió".
    expect(contador(render(0))).toBe("0")
  })

  it("cuenta TODAS, no las de un nivel", () => {
    const mixtas: AlertaDashboard[] = [
      { tipo: "a", mensaje: "Uno", nivel: "info", href: null },
      { tipo: "b", mensaje: "Dos", nivel: "warning", href: null },
      { tipo: "c", mensaje: "Tres", nivel: "error", href: null },
    ]
    expect(contador(renderToStaticMarkup(<AlertasPanel alertas={mixtas} />))).toBe("3")
  })
})

describe("card vacía", () => {
  it("sigue diciendo 'Sin alertas activas.'", () => {
    expect(render(0)).toContain("Sin alertas activas.")
  })

  it("y no ofrece desplegar nada", () => {
    expect(render(0)).not.toContain("group-data-panel-open:rotate-180")
  })
})

describe("estado inicial", () => {
  it("arranca ABIERTA: las alertas son accionables y el punto es que se vean", () => {
    const html = render(3)
    expect(html).toContain("Empleado sin manager asignado ·</p>")
    expect(html).toContain("Empleado sin manager asignado ···</p>")
  })

  it("con alertas sí ofrece plegar", () => {
    expect(render(3)).toContain("group-data-panel-open:rotate-180")
  })
})
