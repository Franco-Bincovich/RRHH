import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { Button } from "@/components/ui/button"
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
 * sobre "disabled".** Con el `Button` de shadcn la razón era que trae `disabled:pointer-events-none`
 * en su markup SIEMPRE, con o sin la prop. Desde la migración al patrón del bloque B las acciones
 * son `<button>` planos que NO traen ninguna variante `disabled:`, así que ahora la razón es la
 * contraria y lleva al mismo lugar: `not.toContain("disabled")` pasaría con el gate borrado. Las
 * dos mitades están abajo, en "la trampa del disabled".
 *
 * **3. Las dos direcciones.** Con `canWrite: true` los botones TIENEN que estar. Sin ese
 * contraste, "no aparecen" pasaría con un componente que no renderiza filas.
 */

const ACTIVO: Cliente = {
  id: "c1", nombre: "Acme", activo: true,
  created_at: "2026-08-01T00:00:00Z", updated_at: null,
}
const BAJA: Cliente = { ...ACTIVO, id: "c2", nombre: "Globex", activo: false }

/*
 * ⚠️ LOS PROPS NUEVOS SON DEL PATRÓN DEL BLOQUE B, no de este test: al migrar la pantalla, la
 * tabla pasó a ser dueña de sus tres estados (carga, error, vacío), que antes tenía la página.
 * Acá se le pasan los valores del camino con datos —sin carga, sin error, sin filtros— para que
 * lo que estos tests miran siga siendo exactamente lo mismo: el gate de escritura y el estado.
 */
function render(clientes: Cliente[], canWrite: boolean): string {
  const html = renderToStaticMarkup(
    <ClientesTabla
      clientes={clientes} canWrite={canWrite} loading={false} error={null}
      onRetry={() => {}} onEdit={() => {}} onDelete={() => {}}
      chips={[]} onLimpiarTodo={() => {}}
    />,
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
    /*
     * 🔴 ESTE TEST CAMBIÓ DE FORMA AL MIGRAR LA TABLA AL PATRÓN DEL BLOQUE B, y el cambio hay que
     * leerlo entero antes de tocarlo.
     *
     * Decía `expect(render([ACTIVO], true)).toContain("disabled:")`, y su punto era: el `Button`
     * de shadcn escribe la clase `disabled:pointer-events-none` en el markup SIEMPRE, con o sin
     * la prop, así que `not.toContain("disabled")` es una aserción que NO PUEDE FALLAR NUNCA —
     * por eso los tests de arriba miran el TEXTO del aria-label.
     *
     * Las acciones de esta tabla ya no son `Button` de shadcn: son `<button>` planos con las
     * clases del patrón (siempre visibles, cambian de color al apuntar), y esas clases no
     * incluyen ninguna variante `disabled:`. O sea que la trampa **ya no está en este markup**.
     *
     * El test no se borra: se parte en las dos mitades que ahora son verdad, porque la conclusión
     * —mirar el aria-label y no la palabra "disabled"— sigue siendo la correcta y ahora lo es por
     * un motivo distinto. La primera mitad conserva la demostración de la trampa sobre el
     * componente que la produce; la segunda fija que esta tabla ya no la tiene.
     */
    // 1. La trampa sigue existiendo donde nació: shadcn emite `disabled:` sin que nadie lo pida.
    expect(renderToStaticMarkup(<Button>Cualquiera</Button>)).toContain("disabled:")
    // 2. Y esta tabla ya no emite ninguna, así que un `not.toContain("disabled")` acá pasaría
    //    igual con el gate borrado — por eso las aserciones de arriba miran el aria-label.
    expect(render([ACTIVO], true)).not.toContain("disabled:")
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
