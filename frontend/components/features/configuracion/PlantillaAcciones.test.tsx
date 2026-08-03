import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { AccionesDelPie } from "./PlantillaAcciones"

/**
 * Guardar una plantilla en modo consolidado ("Todas las empresas") NO se puede: el backend
 * responde 400 `EMPRESA_ID_REQUIRED` porque una plantilla creada desde la UI pertenece a una
 * empresa. Antes eso llegaba como el mensaje crudo *"empresa_id requerido para esta operación"*
 * DESPUÉS de apretar Guardar — jerga de backend, en una pantalla de RRHH, y sin decir que la
 * solución es el selector del sidebar.
 *
 * Ahora el botón está deshabilitado desde que se abre el modal, con el motivo al lado.
 * `Previsualizar` NO se toca: en consolidado el render anda igual y es la mitad útil de la
 * pantalla.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. NO se mockea NADA — y la primera versión de este archivo sí mockeaba `getEmpresaActivaId`,
 *    lo cual era peor que inútil: `AccionesDelPie` recibe `sinEmpresa` por PROP, así que ese
 *    mock no se ejecutaba nunca y el encabezado afirmaba una cobertura que no existía. Acá se
 *    renderiza el componente real y se le pasa el estado directo.
 * 2. Cada test recorre los DOS valores de `sinEmpresa`. Con solo el caso `true`, "el botón está
 *    deshabilitado" pasaría con el botón deshabilitado SIEMPRE, que es la regresión más fácil de
 *    introducir y la que dejaría la pantalla inservible con una empresa elegida.
 * 3. El estado del botón NO se busca como "existe la palabra disabled": el pie tiene DOS botones
 *    y **la clase del `<Button>` incluye SIEMPRE las variantes `disabled:pointer-events-none` y
 *    `disabled:opacity-50`**, esté habilitado o no. La primera versión de estos tests hacía
 *    `toContain("disabled")` y daba verde con el botón HABILITADO — el falso positivo entró por
 *    la puerta de Tailwind. Lo que se mira es el ATRIBUTO `disabled=""` dentro del `<button>` que
 *    contiene el texto, que es lo único que distingue los dos estados.
 *
 * ⚠️ LO QUE QUEDA SIN RED, dicho explícito: que el modal CALCULE bien `sinEmpresa` —o sea la
 * línea `setSinEmpresa(getEmpresaActivaId() === null)` de su useEffect—. `Dialog` de base-ui
 * monta por PORTAL y vitest corre sin jsdom, así que renderizar `<PlantillaModal>` devuelve
 * string vacío (verificado; ver dialog.test.tsx), y un `useEffect` tampoco corre bajo
 * `renderToStaticMarkup`. Son dos limitaciones distintas y las dos apuntan a lo mismo: acá se
 * prueba QUÉ HACE el pie con cada estado, no de dónde sale el estado.
 */

const LLENA = { clave: "bienvenida", asunto: "Hola", cuerpo: "Texto" }

function render(empresa: string | null, extra: Partial<typeof LLENA> = {}) {
  return renderToStaticMarkup(
    <AccionesDelPie
      sinEmpresa={empresa === null}
      guardando={false}
      valores={{ ...LLENA, ...extra }}
      onGuardar={() => {}}
      onPreview={() => {}}
    />,
  )
}

/** El `<button>` que contiene ese texto. null si no está — cada test lo afirma antes de mirar. */
function boton(html: string, texto: string): string | null {
  // `[\s\S]` y no `.` con la flag `s`: el target de tsconfig es anterior a es2018 y `tsc` la
  // rechaza (TS1501), aunque en runtime funcione.
  for (const m of html.matchAll(/<button[^>]*>[\s\S]*?<\/button>/g)) {
    if (m[0].includes(texto)) return m[0]
  }
  return null
}

/**
 * ¿ESE botón está deshabilitado? Por el ATRIBUTO, no por la clase — ver el punto 3 del
 * encabezado. Falla ruidosamente si el botón no está, para que ningún test afirme sobre null.
 */
function deshabilitado(html: string, texto: string): boolean {
  const b = boton(html, texto)
  expect(b, `no se encontró el botón "${texto}"`).not.toBeNull()
  return b!.includes('disabled=""')
}

describe("modo consolidado", () => {
  it("🔴 Guardar queda deshabilitado", () => {
    expect(deshabilitado(render(null), "Guardar")).toBe(true)
  })

  it("y el motivo se lee, sin jerga de backend", () => {
    const html = render(null)
    expect(html).toContain("elegí una empresa en el selector")
    // El mensaje viejo era el del backend. Que no vuelva por copiar y pegar.
    expect(html).not.toContain("empresa_id")
  })

  it("Previsualizar SIGUE habilitado: es la mitad que funciona", () => {
    expect(deshabilitado(render(null), "Previsualizar")).toBe(false)
  })
})

describe("con una empresa seleccionada", () => {
  it("Guardar está habilitado", () => {
    expect(deshabilitado(render("c1"), "Guardar")).toBe(false)
  })

  it("y el aviso NO aparece", () => {
    expect(render("c1")).not.toContain("elegí una empresa")
  })
})

describe("el resto de las guardas del formulario siguen valiendo", () => {
  // Sin esto, "deshabilitado" podría estar viniendo del modo consolidado y taparía que los
  // campos vacíos dejaron de bloquear el guardado.
  it("con una empresa pero sin asunto, Guardar sigue deshabilitado", () => {
    expect(deshabilitado(render("c1", { asunto: "" }), "Guardar")).toBe(true)
  })

  it("con una empresa pero sin cuerpo, también", () => {
    expect(deshabilitado(render("c1", { cuerpo: "" }), "Guardar")).toBe(true)
  })

  it("con una empresa pero sin clave, también", () => {
    expect(deshabilitado(render("c1", { clave: "" }), "Guardar")).toBe(true)
  })
})
