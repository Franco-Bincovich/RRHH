import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { CardsProyecto } from "@/components/features/organigrama/CardsProyecto"
import { periodoTexto, SIN_DEFINIR, valorHoraTexto } from "@/components/features/organigrama/contratoAsignacion"
import type {
  EmpleadoProyectoNodoAPI, OrgProyectosResponse,
} from "@/types/organigrama"

/**
 * El contrato de la asignación en las cards del organigrama: valor hora y período.
 *
 * 🔴 LA REGLA QUE SE PRUEBA: un `valor_hora` de 0 es "no está cargado", NO "cobra cero", y una
 * fecha nula es "no se definió", no "sin límite". Hoy las 31 asignaciones de producción están
 * exactamente así, o sea que el camino "vacío" es el 100% de los casos reales — y es el que un
 * test escrito con datos inventados y bonitos nunca recorrería.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 *  · Los datos traen VARIANTES DISTINTAS, y el caso decisivo (`test_cada_persona_muestra_lo
 *    suyo`) arma DOS grupos de empresa con contratos DIFERENTES en el mismo render. Con una
 *    sola fila, un componente que imprimiera una constante —o el contrato de la primera persona
 *    para todos— pasaría sin que nadie se entere. Es el modo de falla que la consigna pedía
 *    cubrir explícitamente.
 *  · NO se mockea nada: `CardsProyecto` es presentacional puro (recibe `data` por prop, sin
 *    hooks ni fetch), así que corre el componente REAL y los formateadores REALES. Si se
 *    falsearan los formateadores, el test afirmaría sobre su propio doble.
 *  · La ausencia del importe se afirma con `not.toContain("$")` sobre el markup entero, y no
 *    con `not.toContain("0")`: el "0" aparece en clases de Tailwind (`pb-1`, `text-[11px]`,
 *    `py-0.5`) y en los uuids, así que esa aserción pasaría o fallaría por motivos ajenos. El
 *    "$" no aparece en ninguna otra parte de esta card, así que es la señal limpia.
 *
 * ⚠️ vitest corre SIN jsdom: esto es `renderToStaticMarkup`, o sea markup estático y sin
 * `useEffect`. Vale porque lo que se verifica es un `if` de RENDER sobre props, no un efecto.
 * `CardsProyecto` tampoco vive dentro de un acordeón —es una grilla— así que su contenido se
 * monta siempre; aun así `describe("guarda contra el falso verde")` lo comprueba primero.
 */

const EMPRESA_A = "11111111-1111-1111-1111-111111111111"
const EMPRESA_B = "22222222-2222-2222-2222-222222222222"

function persona(over: Partial<EmpleadoProyectoNodoAPI> = {}): EmpleadoProyectoNodoAPI {
  return {
    id: "aaaaaaaa-0000-0000-0000-000000000001",
    nombre: "Ana", apellido: "Perez", iniciales: "AP", cargo: "Analista", rol: "Analista",
    empleado_empresa_id: EMPRESA_A, empleado_empresa_nombre: "ACME",
    total_proyectos: 1,
    valor_hora: 0, fecha_desde: null, fecha_hasta: null,
    ...over,
  }
}

function render(...empleados: EmpleadoProyectoNodoAPI[]): string {
  const data: OrgProyectosResponse = {
    proyectos: [{
      id: "pppppppp-0000-0000-0000-000000000001", nombre: "Proyecto Uno", estado: "activo",
      empresa_id: EMPRESA_A, empresa_nombre: "ACME",
      total_asignados: empleados.length, empleados,
    }],
    empresas_orden: [{ id: EMPRESA_A, nombre: "ACME" }, { id: EMPRESA_B, nombre: "BETA" }],
  }
  return renderToStaticMarkup(<CardsProyecto data={data} />)
}

// ── Los formateadores, aislados ───────────────────────────────────────────────

describe("valorHoraTexto", () => {
  it("formatea un importe real como moneda por hora", () => {
    const texto = valorHoraTexto(1500)
    expect(texto).toContain("1.500")   // agrupación es-AR, no 1,500 ni 1500
    expect(texto).toContain("$")
    expect(texto.endsWith("/h")).toBe(true)
  })

  it.each<[number | null | undefined, string]>([
    [0, "cero: la columna es NOT NULL DEFAULT 0, o sea el estado inicial de las 31 filas"],
    [null, "null defensivo"],
    [undefined, "undefined defensivo"],
    [-5, "negativo: no existe, pero tampoco es un importe que se pueda mostrar"],
    [NaN, "NaN: un parseFloat fallido aguas arriba no debe imprimir '$ NaN'"],
  ])("%s → Sin definir (%s)", (valor, _motivo) => {
    expect(valorHoraTexto(valor)).toBe(SIN_DEFINIR)
  })
})

describe("periodoTexto", () => {
  it("con las dos fechas arma el rango", () => {
    expect(periodoTexto("2026-03-01", "2026-06-30")).toBe("01/03/2026 – 30/06/2026")
  })

  it("con solo la de inicio dice Desde", () => {
    expect(periodoTexto("2026-03-01", null)).toBe("Desde 01/03/2026")
  })

  it("con solo la de fin dice Hasta", () => {
    expect(periodoTexto(null, "2026-06-30")).toBe("Hasta 30/06/2026")
  })

  it("sin ninguna, Sin definir", () => {
    expect(periodoTexto(null, null)).toBe(SIN_DEFINIR)
  })

  it("🔴 NO corre la fecha un día para atrás", () => {
    // Un ISO de solo fecha con `new Date()` se parsea en UTC y en Argentina (UTC−3) sale el día
    // anterior: el 01/03 se mostraría 28/02. Para que falle: usar toLocaleDateString.
    expect(periodoTexto("2026-03-01", null)).toContain("01/03")
  })
})

// ── El componente ─────────────────────────────────────────────────────────────

describe("guarda contra el falso verde", () => {
  it("la card renderiza a la persona: sin esto, todo not.toContain pasa en el vacío", () => {
    const html = render(persona())
    expect(html).toContain("Ana")
    expect(html).toContain("Proyecto Uno")
  })
})

describe("CardsProyecto — el contrato de la asignación", () => {
  it("con valor_hora > 0 muestra el importe", () => {
    const html = render(persona({ valor_hora: 1500 }))
    expect(html).toContain("1.500")
    expect(html).toContain("$")
  })

  it("🔴 con valor_hora = 0 dice Sin definir y NO imprime un importe", () => {
    // El caso de las 31 filas reales. Un "$ 0" afirmaría un acuerdo económico que nadie pactó.
    const html = render(persona({ valor_hora: 0 }))
    expect(html).toContain(SIN_DEFINIR)
    expect(html).not.toContain("$")
  })

  it("con las dos fechas nulas el período dice Sin definir", () => {
    expect(render(persona())).toContain(SIN_DEFINIR)
  })

  it("con las dos fechas cargadas muestra el rango", () => {
    const html = render(persona({ fecha_desde: "2026-03-01", fecha_hasta: "2026-06-30" }))
    expect(html).toContain("01/03/2026")
    expect(html).toContain("30/06/2026")
  })

  it.each([
    ["2026-03-01", null, "Desde 01/03/2026"],
    [null, "2026-06-30", "Hasta 30/06/2026"],
  ])("con una sola fecha (%s / %s) muestra %s", (desde, hasta, esperado) => {
    // Colapsar estos dos en "Sin definir" tiraría el único dato que sí se cargó.
    expect(render(persona({ fecha_desde: desde, fecha_hasta: hasta }))).toContain(esperado)
  })

  it("🔴 cada persona muestra SU contrato, no el de la primera", () => {
    // DOS grupos de empresa con contratos distintos en el mismo render. Para que falle: que el
    // componente imprima una constante, o que reutilice el contrato del primer empleado.
    const html = render(
      persona({ valor_hora: 1500, fecha_desde: "2026-03-01", fecha_hasta: "2026-06-30" }),
      persona({
        id: "aaaaaaaa-0000-0000-0000-000000000002", nombre: "Beto", apellido: "Gomez",
        empleado_empresa_id: EMPRESA_B, empleado_empresa_nombre: "BETA",
        valor_hora: 0, fecha_desde: null, fecha_hasta: null,
      }),
    )
    expect(html).toContain("1.500")        // el de ACME
    expect(html).toContain("01/03/2026")
    expect(html).toContain(SIN_DEFINIR)    // el de BETA, en el mismo markup
  })

  it("el rol se sigue mostrando: el contrato se suma, no reemplaza", () => {
    expect(render(persona({ rol: "Analista" }))).toContain("Analista")
  })
})
