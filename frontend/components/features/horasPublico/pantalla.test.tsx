import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { AvisoIrreversible } from "@/components/features/horasPublico/AvisoIrreversible"
import { CargaForm } from "@/components/features/horasPublico/CargaForm"
import { IdentificacionForm } from "@/components/features/horasPublico/IdentificacionForm"
import { SemanaTabla } from "@/components/features/horasPublico/SemanaTabla"
import {
  FORM_HORAS_VACIO, FORM_LICENCIA_VACIO,
} from "@/components/features/horasPublico/logica"
import type { Semana } from "@/types/horasPublico"

/**
 * Lo que se puede afirmar del MARKUP de la pantalla pública.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * **1. 🔴 La guarda de markup no vacío.** Se renderiza con `renderToStaticMarkup` porque el
 * proyecto corre vitest SIN jsdom. Si un componente devolviera "" —porque revienta, porque lo
 * envuelve un portal, porque alguien le mete un `return null`— TODAS las aserciones negativas
 * pasarían igual, y el test estaría afirmando que un componente ROTO no muestra campos. Por eso
 * cada render pasa por `_render`, que exige contenido antes de devolverlo.
 *
 * **2. 🔴 Las dos direcciones.** "En modo licencia no están los campos de horas" no significa
 * nada sin "en modo horas SÍ están": lo primero pasa con un formulario que no renderiza nada.
 * Cada bloque afirma la presencia y la ausencia.
 *
 * **3. La trampa del `disabled`.** El markup de shadcn trae la clase `disabled:` con y sin la
 * prop, así que `not.toContain("disabled")` es una aserción que NO PUEDE FALLAR. Por eso el
 * "no se puede enviar con obligatorios vacíos" se prueba sobre `puedeEnviar()` —función pura,
 * en `logica.test.ts`— y acá solo se deja constancia de que el atributo REAL aparece.
 *
 * ⚠️ La PÁGINA (`app/horas/page.tsx`) no se renderiza acá: su estado inicial depende de un
 * `useEffect` que lee sessionStorage, y sin jsdom ese efecto no corre. Lo que la página decide
 * está en `logica.ts` y se prueba allá.
 */

const SEMANA: Semana = {
  desde: "2026-08-17", hasta: "2026-08-23", total_horas: 6,
  cargas: [{ fecha: "2026-08-18", cliente_nombre: "Acme", proyecto_texto: null,
             tarea_texto: "Reunión", horas: 4, modalidad: "home_office" }],
  licencias: [{ fecha_desde: "2026-08-19", fecha_hasta: "2026-08-19", dias: 1,
                observaciones: "Trámite" }],
}

function _render(nodo: React.ReactElement): string {
  const html = renderToStaticMarkup(nodo)
  // 🔴 GUARDA: sin esto, un componente que devuelve "" pasa toda aserción negativa.
  expect(html.length).toBeGreaterThan(80)
  return html
}

function form(modo: "horas" | "licencia") {
  return _render(
    <CargaForm modo={modo} onModo={() => {}} horas={FORM_HORAS_VACIO} onHoras={() => {}}
               licencia={FORM_LICENCIA_VACIO} onLicencia={() => {}}
               clientes={[{ id: "c1", nombre: "Acme" }]} errores={{}} enviando={false}
               hoy={new Date("2026-08-20T12:00:00Z")} />,
  )
}

describe("el formulario no aparece antes de identificarse", () => {
  it("el paso 1 pide el DNI y nada más", () => {
    const html = _render(
      <IdentificacionForm dni="" onDni={() => {}} enviando={false} onSubmit={() => {}} />)
    expect(html).toContain("Ingresá tu DNI")
    // Ninguno de los campos de carga puede estar en la pantalla de identificación.
    for (const campo of ["Modalidad", "Cliente", "Horas trabajadas", "Licencia", "Observaciones"]) {
      expect(html).not.toContain(campo)
    }
  })

  it("el contraste: el formulario de carga SÍ los tiene", () => {
    // Sin esto, "el paso 1 no los muestra" pasaría con un CargaForm que no renderiza nada.
    const html = form("horas")
    expect(html).toContain("Modalidad")
    expect(html).toContain("Cliente")
  })
})

describe("elegir licencia desactiva la carga de horas", () => {
  it("en modo licencia NO se renderizan los campos de horas", () => {
    // 🔴 No se deshabilitan: NO EXISTEN. Un campo gris sugeriría que está bloqueado; la verdad
    // es que el endpoint de licencia ni siquiera acepta esos campos.
    const html = form("licencia")
    expect(html).not.toContain('id="horas"')
    expect(html).not.toContain('id="cliente"')
    expect(html).not.toContain('id="modalidad"')
    expect(html).not.toContain('id="proyecto"')
  })

  it("en modo licencia SÍ están desde, hasta y observaciones", () => {
    const html = form("licencia")
    expect(html).toContain('id="desde"')
    expect(html).toContain('id="hasta"')
    expect(html).toContain('id="observaciones"')
  })

  it("en modo horas es exactamente al revés", () => {
    const html = form("horas")
    expect(html).toContain('id="horas"')
    expect(html).toContain('id="cliente"')
    expect(html).not.toContain('id="desde"')
    expect(html).not.toContain('id="hasta"')
  })

  it("el selector de modo marca cuál está activo", () => {
    expect(form("horas")).toContain('aria-pressed="true"')
    expect(form("licencia")).toContain('aria-pressed="true"')
  })
})

describe("no se puede enviar con obligatorios vacíos", () => {
  it("el botón sale con el atributo disabled real", () => {
    // ⚠️ Se afirma el ATRIBUTO `disabled=""`, no la palabra "disabled": la clase
    // `disabled:pointer-events-none` de shadcn está SIEMPRE, así que buscarla no probaría nada.
    // La regla de negocio (qué campos son obligatorios) se prueba en `logica.test.ts`.
    expect(form("horas")).toContain('disabled=""')
  })

  it("el select de cliente ofrece los que llegaron y arranca sin elegir", () => {
    const html = form("horas")
    expect(html).toContain("Acme")
    expect(html).toContain("Elegí uno")
  })
})

describe("el aviso de irreversible está visible", () => {
  it("dice que no se puede editar ni borrar, y a quién avisar", () => {
    const html = _render(<AvisoIrreversible />)
    expect(html).toContain("no se puede editar ni borrar")
    expect(html).toContain("Capital Humano")
  })

  it("muestra los dos límites, tomados del backend y no escritos a mano", () => {
    const html = _render(<AvisoIrreversible />)
    expect(html).toContain("30 días")
    expect(html).toContain("12 horas")
  })
})

describe("la tabla de la semana es de solo lectura", () => {
  it("muestra las cargas y las licencias juntas", () => {
    const html = _render(<SemanaTabla semana={SEMANA} />)
    expect(html).toContain("Acme")
    expect(html).toContain("Reunión")
    expect(html).toContain("Licencia")
    expect(html).toContain("Trámite")
  })

  it("🔴 no ofrece editar ni borrar", () => {
    // El empleado no puede corregir: el backend no expone update ni delete para él. Un botón
    // acá sería una promesa que el sistema no puede cumplir.
    const html = _render(<SemanaTabla semana={SEMANA} />)
    for (const accion of ["Editar", "Eliminar", "Borrar"]) {
      expect(html).not.toContain(accion)
    }
  })

  it("con la semana vacía lo dice, en vez de mostrar una tabla en blanco", () => {
    const html = _render(
      <SemanaTabla semana={{ ...SEMANA, cargas: [], licencias: [], total_horas: 0 }} />)
    expect(html).toContain("Todavía no cargaste nada")
  })

  it("las fechas no se corren un día por zona horaria", () => {
    // Se cortan del ISO en vez de pasar por `new Date`, que interpreta en UTC.
    expect(_render(<SemanaTabla semana={SEMANA} />)).toContain("18/08")
  })
})
