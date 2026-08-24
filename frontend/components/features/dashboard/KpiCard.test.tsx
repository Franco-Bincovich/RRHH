import { Users } from "lucide-react"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import type { KpiCardData, TonoKpi } from "./_kpisDashboard"
import { KpiCard } from "./KpiCard"

/**
 * La card de KPI: **el fondo se despega, el número no** (§6).
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. 🔴 No alcanza con buscar `bg-warning-wash` en el markup: eso pasaría igual si el wash
 *    estuviera pintado sobre el número. Los tests **localizan el `<p>` del valor y verifican su
 *    clase por separado** de la del contenedor. Es la única forma de distinguir "card ámbar" de
 *    "número ámbar", que es exactamente la distinción que §6 hace.
 * 2. El valor del fixture es una palabra (`VALOR`), no un número: buscarlo en el markup no puede
 *    chocar con un dígito de una clase de Tailwind.
 * 3. Cada aserción sobre el tono lleva su CONTRASTE en neutro. Sin él, una card que ignorara el
 *    tono y pintara siempre lo mismo pasaría la mitad de los tests.
 */

const BASE: KpiCardData = {
  title: "Ingresos próximos 30 días", value: "VALOR", icon: Users,
  description: "descripción", tono: "neutro",
}

const render = (kpi: Partial<KpiCardData>) =>
  renderToStaticMarkup(<KpiCard kpi={{ ...BASE, ...kpi }} />)

/** El tag del contenedor de la card: `div` sin destino, `a` cuando la card linkea. */
function tagCard(html: string): string {
  const m = html.match(/^<([a-z]+)[ >]/)
  expect(m, "cambió la forma de la card: el markup ya no arranca con el contenedor").not.toBeNull()
  return m![1]
}

/**
 * La clase del contenedor de la card.
 *
 * ⚠️ NO ancla el tag ni la posición del atributo, al revés que la versión anterior
 * (`/^<div class="/`). La card pasó a `<Card>` —que emite `data-slot="card"` antes de la clase— y
 * ahora es un `<a>` cuando lleva destino: anclar cualquiera de las dos cosas volvería a romper el
 * helper con el próximo cambio de envoltorio, sin que nada del FONDO —que es lo que este archivo
 * mira— haya cambiado.
 */
function claseCard(html: string): string {
  const m = html.match(/^<[a-z]+[^>]*\sclass="([^"]*)"/)
  expect(m, "cambió la forma de la card: el contenedor ya no trae class").not.toBeNull()
  return m![1]
}

/** La clase del <p> que contiene el VALOR, no la del contenedor. */
function claseDelValor(html: string): string {
  const m = html.match(/<p class="([^"]*)"[^>]*>VALOR<\/p>/)
  expect(m, "no encontré el <p> del valor: cambió la estructura de la card").not.toBeNull()
  return m![1]
}

describe("el fondo semántico va en la card, no en el número", () => {
  it("con tono de atención, el wash está en el contenedor", () => {
    expect(claseCard(render({ tono: "atencion" }))).toContain("bg-warning-wash")
  })

  it("y el número sigue en text-foreground, sin color semántico", () => {
    const clase = claseDelValor(render({ tono: "atencion" }))
    expect(clase).toContain("text-foreground")
    expect(clase).not.toContain("warning")
    expect(clase).not.toContain("wash")
  })

  it("EL CONTRASTE: en neutro la card NO lleva ningún wash", () => {
    const html = render({ tono: "neutro" })
    expect(claseCard(html)).toContain("bg-card")
    expect(claseCard(html)).not.toContain("wash")
    // El número se pinta igual en los dos tonos: es lo que hace que el fondo sea la única señal.
    expect(claseDelValor(html)).toBe(claseDelValor(render({ tono: "atencion" })))
  })

  it("los cuatro tonos existen y ninguno toca el color del número", () => {
    const tonos: TonoKpi[] = ["neutro", "atencion", "riesgo", "bien"]
    expect(tonos).toHaveLength(4) // guarda: sin tonos el forEach no compara nada
    tonos.forEach((tono) => {
      expect(claseDelValor(render({ tono }))).toContain("text-foreground")
    })
    // Y cada uno pinta un fondo distinto: un Record con cuatro claves al mismo valor sería un
    // mecanismo que existe y no hace nada.
    const fondos = tonos.map((tono) => claseCard(render({ tono })))
    expect(new Set(fondos).size).toBe(4)
  })
})

describe("el detalle", () => {
  it("se renderiza cuando la card agrupa (headcount por empresa)", () => {
    const html = render({ detalle: [{ etiqueta: "KARSTEC", valor: "19" }] })
    expect(html).toContain("KARSTEC")
    expect(html).toContain(">19<")
  })

  it("y no deja un <ul> vacío cuando no hay nada que repartir", () => {
    expect(render({ detalle: [] })).not.toContain("<ul")
    expect(render({})).not.toContain("<ul")
  })
})

/**
 * 🔴 EL MOVIMIENTO YA NO DEPENDE DEL LINK, Y ESTE BLOQUE SE DIO VUELTA POR ESO (23/8/2026).
 * Acá se afirmaba lo contrario —*"sin href es un `<div>` quieto, sin hover"*— y era la decisión
 * vigente hasta que Franco la revirtió: en una grilla, que unas tarjetas respondan al puntero y
 * otras no se lee como que algunas están deshabilitadas. Ahora **las dos ramas se mueven** y lo
 * único que el `href` decide es si además NAVEGA.
 *
 * ⚠️ La aserción no se borró, se INVIRTIÓ: si se borrara, la rama sin `href` se quedaría sin
 * nadie mirándola y podría perder el movimiento sin que ningún test lo note. Lo que se prueba
 * ahora es la igualdad (las dos llevan la elevación) más la diferencia real (el tag y el href).
 *
 * ⚠️ Se afirma sobre `hover:-translate-y-[3px]`, que es el literal que `card.tsx` pone en
 * `interactive` y que `decisionesVisuales.test.ts` fija contra la cita de §2. Si esa decisión
 * cambia de forma, rojea allá (por la fuente) y acá (por el consumidor), que es lo que se quiere.
 */
describe("toda card de KPI se mueve; el destino sólo decide si además navega", () => {
  it("con href es un <a> a esa ruta", () => {
    const html = render({ href: "/empleados?estado=activo" })
    expect(tagCard(html)).toBe("a")
    expect(html).toContain('href="/empleados?estado=activo"')
  })

  it("y ahí SÍ lleva la elevación de §2, que es lo que dice que se puede apretar", () => {
    expect(claseCard(render({ href: "/vacantes" }))).toContain("hover:-translate-y-[3px]")
  })

  it("sin href es un <div> y NO navega, pero se mueve igual", () => {
    const html = render({})
    expect(tagCard(html)).toBe("div")
    expect(html).not.toContain("href=")
    expect(claseCard(html)).toContain("hover:-translate-y-[3px]")
  })

  it("EL CONTRASTE: la elevación es la MISMA con y sin destino", () => {
    const elevacion = (h: string) =>
      claseCard(h).split(" ").filter((c) => c.startsWith("hover:")).sort().join(" ")
    expect(elevacion(render({}))).toBe(elevacion(render({ href: "/vacantes" })))
    expect(elevacion(render({}))).toContain("hover:-translate-y-[3px]")
  })

  it("el interior no cambia: lo único que cambia es el envoltorio", () => {
    const sin = render({})
    const con = render({ href: "/vacantes" })
    // Hasta el ÚLTIMO "<": el cierre del envoltorio (`</div>` vs `</a>`) es justamente lo que
    // sí tiene que diferir, y compararlo haría fallar el test por la única diferencia esperada.
    const interior = (h: string) => h.slice(h.indexOf("<div class="), h.lastIndexOf("<"))
    expect(interior(con)).toBe(interior(sin))
  })

  it("y el fondo semántico sigue siendo el de su tono aunque linkee", () => {
    expect(claseCard(render({ tono: "atencion", href: "/vacantes" }))).toContain("bg-warning-wash")
  })
})

describe("lo que siempre está", () => {
  it("título, valor y descripción", () => {
    const html = render({})
    expect(html).toContain("Ingresos próximos 30 días")
    expect(html).toContain("VALOR")
    expect(html).toContain("descripción")
  })

  it("el valor va en cifras tabulares (el sistema de diseño las pide en todos los números)", () => {
    expect(claseDelValor(render({}))).toContain("tabular-nums")
  })
})
