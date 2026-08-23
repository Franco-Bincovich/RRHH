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
 * 3. 🔴 El acordeón es el real de base-ui, sin mockear: un panel PLEGADO no renderiza su
 *    contenido (verificado en ConfigSection.test.tsx). Eso es lo que hace afirmable el estado
 *    inicial en las dos direcciones — y por eso el test de abajo cambió de signo el 23/8/2026:
 *    decía "arranca ABIERTA" y buscaba los mensajes EN el markup; ahora afirma que NO están.
 *    Si alguien le devuelve el `defaultValue`, los mensajes reaparecen y rojea.
 *    ⚠️ Un test que buscara los mensajes con `not.toContain` a secas sería vacuo: pasaría también
 *    con el componente entero borrado. Por eso cada aserción de ausencia va acompañada de la
 *    presencia del ENCABEZADO (título y contador), que plegada sí se renderiza.
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
  it("su mensaje vive en el panel, así que plegada no se ve — y el contador sí", () => {
    // "Sin alertas activas." es contenido del panel, no un slot aparte del encabezado. Plegada,
    // la respuesta a "cuántas hay" la da el contador en 0, que es la misma información.
    const html = render(0)
    expect(html).not.toContain("Sin alertas activas.")
    expect(contador(html)).toBe("0")
  })

  it("y se puede desplegar igual, como cualquier otra", () => {
    // El chevron está siempre: plegar una card con "Sin alertas activas." no es útil, pero un
    // chevron que a veces está y a veces no obliga al usuario a descubrir la regla.
    expect(render(0)).toContain("group-data-panel-open:rotate-180")
  })
})

describe("estado inicial", () => {
  /**
   * 🔴 ARRANCA PLEGADA — la regla es "ningún desplegable nace desplegado", con dos excepciones
   * declaradas en `components/ui/barridoAcordeones.test.ts`, y ésta no es una de ellas. Este
   * panel es la salud del SISTEMA (tablas vacías, campos del padrón sin cargar): una deuda de
   * carga que se arrastra hace meses, no algo que se hace esta semana. Lo que sí es de esta
   * semana —"Requiere tu atención"— es lo único que queda abierto, y que sea el único es lo que
   * hace que estar abierto vuelva a significar algo.
   */
  it("arranca PLEGADA: ninguno de sus mensajes está en el markup", () => {
    const html = render(3)
    expect(html).not.toContain("Empleado sin manager asignado ·</p>")
    expect(html).not.toContain("Empleado sin manager asignado ···</p>")
  })

  it("EL CONTRASTE: el encabezado SÍ está, o sea que el panel existe y sólo está plegado", () => {
    // Sin esta aserción, la de arriba pasaría con el componente devolviendo null.
    const html = render(3)
    expect(html).toContain("Alertas activas")
    expect(contador(html)).toBe("3")
  })

  it("con alertas ofrece desplegar", () => {
    expect(render(3)).toContain("group-data-panel-open:rotate-180")
  })
})
