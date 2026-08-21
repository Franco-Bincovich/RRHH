import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { EventosTabla } from "@/components/features/eventos/EventosTabla"
import type { Evento } from "@/types/evento"

/**
 * La tabla de la agenda: qué ofrece según el permiso y según el estado del evento.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * **1. La guarda de markup no vacío.** Se renderiza con `renderToStaticMarkup` porque el
 * proyecto corre vitest SIN jsdom. Si el componente devolviera "" —porque revienta, porque lo
 * envuelve un portal, porque alguien lo cambia a `return null`— entonces `not.toContain(...)`
 * pasaría igual y el test estaría afirmando que un componente ROTO no muestra botones. Por eso
 * cada render pasa primero por `markupNoVacio`.
 *
 * **2. Los botones se OMITEN, no se deshabilitan — y por eso se afirma sobre el TEXTO y no sobre
 * "disabled".** El `Button` de shadcn trae la clase `disabled:pointer-events-none` SIEMPRE, con
 * o sin la prop: `expect(html).not.toContain("disabled")` es una aserción que no puede fallar
 * nunca. Es la trampa que dejó escrita `ClientesTabla.test.tsx`.
 *
 * **3. Las dos direcciones, en los dos ejes.** Con `canWrite: true` los botones TIENEN que
 * estar; y el evento PENDIENTE y el RESUELTO se renderizan los dos, porque lo que distingue al
 * botón de resolver del de reabrir es solo el estado. Con un único evento en la lista, "dice
 * Resolver" y "dice siempre Resolver" serían indistinguibles.
 */

const PENDIENTE: Evento = {
  id: "e1", empresa_id: "emp1", nombre: "Feriado puente", fecha: "2026-12-08",
  descripcion: "Se trabaja medio día", dias_aviso: 7, es_publica: true,
  resuelta: false, resuelta_at: null, resuelta_por: null, resuelta_por_nombre: null,
  created_by: "u1", created_by_nombre: "Sofía Gómez", empresa_nombre: "KARSTEC",
  created_at: "2026-01-01T00:00:00Z", updated_at: null,
}

const RESUELTO: Evento = {
  ...PENDIENTE, id: "e2", nombre: "Cierre de balance", resuelta: true,
  resuelta_at: "2026-11-01T00:00:00Z", resuelta_por: "u1", resuelta_por_nombre: "Sofía Gómez",
  es_publica: false,
}

/*
 * ⚠️ LOS PROPS NUEVOS SON DEL PATRÓN DEL BLOQUE B, no de este test: al migrar la pantalla, la
 * tabla pasó a ser dueña de sus tres estados (carga, error, vacío), que antes tenía la página.
 * Acá se le pasan los valores del camino con datos —sin carga, sin error, sin filtros— para que
 * lo que estos tests miran siga siendo exactamente lo mismo: el gate de escritura y el estado
 * de cada evento.
 */
function render(eventos: Evento[], canWrite: boolean): string {
  const html = renderToStaticMarkup(
    <EventosTabla eventos={eventos} canWrite={canWrite}
                  loading={false} error={null} onRetry={() => {}}
                  chips={[]} onLimpiarTodo={() => {}}
                  onEdit={() => {}} onDelete={() => {}} onResuelta={() => {}} />,
  )
  // 🔴 GUARDA: sin esto, un componente que renderiza "" pasaría todas las aserciones negativas.
  expect(html.length).toBeGreaterThan(100)
  expect(html).toContain(eventos[0].nombre)
  return html
}

describe("sin permiso de escritura no hay acciones", () => {
  it("no ofrece editar, eliminar ni resolver", () => {
    const html = render([PENDIENTE, RESUELTO], false)
    for (const accion of ["Editar", "Eliminar", "Resolver", "Reabrir"]) {
      expect(html).not.toContain(accion)
    }
  })

  it("pero SÍ muestra los datos: el valor es información, no una acción", () => {
    const html = render([PENDIENTE], false)
    expect(html).toContain("Feriado puente")
    expect(html).toContain("7 días antes")
  })
})

describe("con permiso de escritura", () => {
  it("ofrece las tres acciones sobre un evento pendiente", () => {
    const html = render([PENDIENTE], true)
    expect(html).toContain("Editar Feriado puente")
    expect(html).toContain("Eliminar Feriado puente")
    expect(html).toContain("Resolver Feriado puente")
  })

  it("🔴 sobre uno RESUELTO el mismo botón dice Reabrir", () => {
    // Un solo handler y un solo endpoint: lo que cambia es el valor que se manda. Si el botón
    // dijera siempre "Resolver", el usuario no tendría cómo saber que se puede volver atrás.
    const html = render([RESUELTO], true)
    expect(html).toContain("Reabrir Cierre de balance")
    expect(html).not.toContain("Resolver Cierre de balance")
  })
})

describe("lo que la tabla dice de cada fila", () => {
  it("distingue el evento del equipo del privado", () => {
    const html = render([PENDIENTE, RESUELTO], true)
    expect(html).toContain("Del equipo")
    expect(html).toContain("Privado")
  })

  it("dice quién lo resolvió, y no lo dice cuando nadie lo resolvió", () => {
    expect(render([RESUELTO], true)).toContain("Resuelto por Sofía Gómez")
    expect(render([PENDIENTE], true)).toContain("Pendiente")
  })

  it("🔴 la fecha sale en el día correcto, no uno antes", () => {
    // `new Date("2026-12-08")` parsea como UTC medianoche y en Argentina (UTC-3) se renderiza
    // como el 07/12. El `T00:00:00` del componente es lo que lo evita, y esto lo fija.
    expect(render([PENDIENTE], true)).toContain("08/12/2026")
  })
})
