import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { ClientesTabla } from "@/components/features/clientes/ClientesTabla"
import type { Cliente } from "@/types/cliente"

/**
 * Sin permiso de escritura, la tabla no ofrece acciones de escritura.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * **1. La guarda de markup no vacío.** Se renderiza con `renderToStaticMarkup` porque el
 * proyecto corre vitest SIN jsdom. Si el componente devolviera "" —porque revienta, porque lo
 * envuelve un portal, porque cambia a un `return null`— entonces `not.toContain("Editar")`
 * pasaría igual, y el test estaría afirmando que un componente ROTO no muestra botones. Por eso
 * cada render pasa primero por `markupNoVacio`. Es exactamente por lo que ClienteModal NO se
 * testea acá: usa `Dialog` de Radix, que monta por PORTAL, y a string sale vacío siempre —
 * un test suyo pasaría con el formulario entero borrado. Su lógica se testea como función pura
 * (validarNombre, mensajeDeError).
 *
 * **2. Los botones se OMITEN, no se deshabilitan — y por eso se afirma sobre el texto y no
 * sobre "disabled".** El `Button` de shadcn trae la clase `disabled:pointer-events-none` en su
 * markup SIEMPRE, con o sin la prop: `expect(html).not.toContain("disabled")` es una aserción
 * que NO PUEDE FALLAR NUNCA. La prueba está abajo, en `test_la_trampa_del_disabled`.
 *
 * **3. Las dos direcciones.** Con `canWrite: true` los botones TIENEN que estar. Sin ese
 * contraste, "no aparecen" pasaría con un componente que no renderiza filas.
 */

const ACTIVO: Cliente = {
  id: "c1", nombre: "Acme", activo: true,
  created_at: "2026-08-01T00:00:00Z", updated_at: null,
}
const BAJA: Cliente = { ...ACTIVO, id: "c2", nombre: "Globex", activo: false }

function render(clientes: Cliente[], canWrite: boolean): string {
  const html = renderToStaticMarkup(
    <ClientesTabla clientes={clientes} canWrite={canWrite} onEdit={() => {}} onDelete={() => {}} />,
  )
  // 🔴 GUARDA: sin esto, un componente que renderiza "" pasaría todas las aserciones negativas.
  expect(html.length).toBeGreaterThan(50)
  expect(html).toContain("Cliente")
  return html
}

describe("ClientesTabla — gate de escritura", () => {
  it("sin canWrite no ofrece editar ni dar de baja", () => {
    const html = render([ACTIVO], false)
    expect(html).not.toContain("Editar Acme")
    expect(html).not.toContain("Dar de baja Acme")
    expect(html).not.toContain("Acciones")
  })

  it("con canWrite ofrece las dos acciones", () => {
    const html = render([ACTIVO], true)
    expect(html).toContain("Editar Acme")
    expect(html).toContain("Dar de baja Acme")
    expect(html).toContain("Acciones")
  })

  it("la trampa del disabled: afirmarlo no probaría nada", () => {
    // El markup de shadcn trae la clase `disabled:` con y sin la prop. Este test existe para
    // dejar constancia de por qué las aserciones de arriba miran el TEXTO del aria-label y no
    // la palabra "disabled": si alguien "mejora" el gate a `disabled={!canWrite}`, esta
    // aserción seguiría pasando y el botón seguiría clickeable para gerencia_lectura.
    expect(render([ACTIVO], true)).toContain("disabled:")
  })
})

describe("ClientesTabla — estado del cliente", () => {
  it("distingue activo de dado de baja", () => {
    const html = render([ACTIVO, BAJA], true)
    expect(html).toContain("Activo")
    expect(html).toContain("Dado de baja")
  })

  it("un cliente ya dado de baja no ofrece volver a darlo de baja", () => {
    const html = render([BAJA], true)
    expect(html).toContain("Editar Globex")          // sí se puede reactivar desde el modal
    expect(html).not.toContain("Dar de baja Globex")
  })

  it("renderiza una fila por cliente: la key es el id, no el nombre", () => {
    // ⚠️ Desde la migración 108 la base NO permite dos clientes con el mismo nombre (el índice
    // único pasó a ser global). El test se conserva igual porque lo que afirma es una propiedad
    // del COMPONENTE —no deduplica por nombre— y no debería depender de lo que la base permita.
    const otro: Cliente = { ...ACTIVO, id: "c3" }
    const html = render([ACTIVO, otro], false)
    expect(html.split("Acme").length - 1).toBe(2)
  })
})
