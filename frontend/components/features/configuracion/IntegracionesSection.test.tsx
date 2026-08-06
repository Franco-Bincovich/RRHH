import { renderToStaticMarkup } from "react-dom/server"
import { Accordion } from "@base-ui/react/accordion"
import { describe, expect, it, vi } from "vitest"

import type { Integracion } from "@/services/integraciones"

/**
 * El bloque de Google: qué control se ofrece según el estado de la cuenta conectada.
 *
 *   ya es la casilla        → chip "Casilla del sistema", y NINGÚN botón de designar.
 *   no lo es, puede enviar  → botón habilitado.
 *   no lo es, no puede      → botón deshabilitado (designarla daría un 403 en el primer mail).
 *
 * No se desdesigna: la casilla es única y se cambia designando otra. Por eso el caso "ya es la
 * casilla" afirma la AUSENCIA del botón, no que esté deshabilitado.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 *  · Se falsea `useIntegraciones` y NADA más. El componente corre entero: el ternario del
 *    chip, el `disabled` compuesto y el <ConfigSection> real. Con el componente mockeado no
 *    quedaría nada que probar; con el hook real, `loading` arranca en true y —sin jsdom, o sea
 *    sin `useEffect`— la sección se quedaría en el skeleton para siempre y todo `not.toContain`
 *    pasaría en el vacío.
 *  · El acordeón se abre a mano (`defaultValue={["google"]}`). ConfigSection NO monta su panel
 *    plegado, y en la página real esta sección nace PLEGADA: sin abrirla, el markup no tendría
 *    ni el chip ni el botón y los tres casos darían el mismo verde. `test_el_panel_esta_abierto`
 *    es la guarda contra ese falso verde: si el panel dejara de renderizarse, rojea ahí primero.
 *  · `botonDe` recorta el <button> que contiene la etiqueta, en vez de buscar el atributo en la
 *    página entera: hay DOS botones en esa fila, y sin recortar, el `disabled` de Desconectar
 *    haría pasar el caso del botón de designar. El contrapeso habilitado lo confirma.
 *  · 🔴 Se busca `disabled=""` —el ATRIBUTO— y no la palabra suelta: la clase del Button trae
 *    `disabled:pointer-events-none disabled:opacity-50`, así que un `toContain("disabled")` da
 *    positivo SIEMPRE, con el botón habilitado o no. Escrito así primero, los dos casos de
 *    "está deshabilitado" pasaban sin mirar nada; los delataron sus contrapesos.
 *
 * El gate de permisos NO se prueba acá: la sección entera se muestra u oculta un escalón más
 * arriba, en page.test.tsx, que corre el `puede` real.
 */

const estado = vi.fn()
vi.mock("@/components/features/configuracion/useIntegraciones", () => ({
  useIntegraciones: () => estado(),
}))

const { IntegracionesSection } = await import(
  "@/components/features/configuracion/IntegracionesSection"
)

const BASE: Integracion = {
  tipo: "google",
  email_cuenta: "rrhh@karstec.com",
  activo: true,
  connected: true,
  puede_enviar: true,
  es_remitente_sistema: false,
}

const DESIGNAR = "Usar como casilla del sistema"
const CHIP = "Casilla del sistema"

function render(google: Partial<Integracion>, ocupado: Record<string, boolean> = {}): string {
  estado.mockReturnValue({
    loading: false,
    ocupado,
    google: { ...BASE, ...google },
    anthropic: undefined,
    zernio: undefined,
    guardarKey: vi.fn(),
    conectarGoogle: vi.fn(),
    desconectarGoogle: vi.fn(),
    designarRemitente: vi.fn(),
  })
  return renderToStaticMarkup(
    <Accordion.Root defaultValue={["google"]} multiple>
      <IntegracionesSection />
    </Accordion.Root>,
  )
}

/** El <button ...> que contiene `etiqueta`, sin el resto de la fila. */
function botonDe(html: string, etiqueta: string): string {
  const fin = html.indexOf(etiqueta)
  expect(fin, `no se renderizó el botón "${etiqueta}"`).toBeGreaterThan(-1)
  return html.slice(html.lastIndexOf("<button", fin), fin)
}

/** ¿Ese botón salió con el ATRIBUTO disabled? Ver la nota del encabezado sobre `disabled:`. */
function deshabilitado(html: string, etiqueta: string): boolean {
  return botonDe(html, etiqueta).includes('disabled=""')
}

describe("guarda contra el falso verde", () => {
  it("el panel está abierto y el contenido se renderiza", () => {
    // Si esto falla, TODOS los not.toContain de abajo pasan sin haber mirado nada.
    expect(render({})).toContain("rrhh@karstec.com")
  })
})

describe("ya es la casilla del sistema", () => {
  it("muestra el chip", () => {
    expect(render({ es_remitente_sistema: true })).toContain(CHIP)
  })

  it("y NO ofrece el botón de designar: no se desdesigna, se designa otra", () => {
    expect(render({ es_remitente_sistema: true })).not.toContain(DESIGNAR)
  })
})

describe("todavía no es la casilla", () => {
  it("ofrece el botón y no el chip", () => {
    const html = render({ es_remitente_sistema: false })
    expect(html).toContain(DESIGNAR)
    expect(html).not.toContain(CHIP)
  })

  it("sin permiso de envío el botón está deshabilitado", () => {
    // Designarla dejaría una casilla que se ve configurada y falla con 403 al primer mail.
    expect(deshabilitado(render({ puede_enviar: false }), DESIGNAR)).toBe(true)
  })

  it("con permiso de envío está habilitado", () => {
    // El contrapeso del anterior: sin esto, "está deshabilitado" podría ser siempre cierto.
    expect(deshabilitado(render({ puede_enviar: true }), DESIGNAR)).toBe(false)
  })

  it("mientras la designación está en vuelo está deshabilitado", () => {
    const html = render({ puede_enviar: true }, { "google-remitente": true })
    expect(deshabilitado(html, DESIGNAR)).toBe(true)
  })

  it("el bloqueo es POR BOTÓN: desconectar en vuelo no deshabilita el de designar", () => {
    // useOcupado es un mapa por clave justamente para esto; con un flag único, rojea.
    const html = render({ puede_enviar: true }, { "google-off": true })
    expect(deshabilitado(html, DESIGNAR)).toBe(false)
    expect(deshabilitado(html, "Desconectar")).toBe(true)
  })
})
