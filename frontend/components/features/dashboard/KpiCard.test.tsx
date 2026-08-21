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

/** La clase del contenedor de la card (el primer <div> del markup). */
function claseCard(html: string): string {
  const m = html.match(/^<div class="([^"]*)"/)
  expect(m, "cambió la forma de la card: el markup ya no arranca con el div contenedor").not.toBeNull()
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
