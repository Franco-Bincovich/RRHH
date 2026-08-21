import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { ERROR_HISTORIAL, HistorialTabla, VACIO_HISTORIAL } from "./HistorialTabla"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import type { MailEnviado } from "@/types/plantillas"

/**
 * Los tres renders del historial tienen que ser DISTINGUIBLES entre sí: cargando, error, y lista
 * (vacía o con datos).
 *
 * 🔴 EL CASO QUE IMPORTA ES EL DEL MEDIO. Un `.catch` que pinte lista vacía haría que la pantalla
 * diga "todavía no se envió ningún mail" cuando lo que hubo fue un fallo de red — una afirmación
 * FALSA sobre los datos, que manda al usuario a buscar el problema donde no está. Es literalmente
 * el bug que este repo arregló hace dos sesiones ("no hay empleados" con 31 activos en la base).
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. Los tres estados se afirman UNO CONTRA OTRO, no cada uno por su lado: el de error exige que
 *    el texto de vacío NO esté, y el de vacío exige que el de error NO esté. Con aserciones
 *    sueltas, un componente que mostrara siempre el mismo bloque pasaría los tres.
 * 2. Los textos se IMPORTAN del componente (`ERROR_HISTORIAL`, `VACIO_HISTORIAL`) en vez de
 *    copiarse: si alguien los edita, el test sigue afirmando la DISTINCIÓN y no el texto viejo.
 *    Hay un caso que exige que los dos sean distintos — si se igualaran, todo lo demás sería vacuo.
 * 3. GUARDA DE MARKUP en cada render: si el componente no montara, la salida sería "" y todos los
 *    `not.toContain` pasarían sin haber mirado nada. (Es lo que pasa con un componente dentro de
 *    un acordeón plegado o del portal de un Dialog, las dos trampas conocidas de esta suite.)
 *
 * ⚠️ LO QUE QUEDA SIN RED, explícito: el CLIC en "Reintentar". vitest corre sin jsdom, así que se
 * verifica que el botón esté en el markup, no que dispare `onReintentar`. El cableado del hook
 * (`recargar` → re-fetch) tampoco se puede ejercitar acá.
 */

const ENVIADO: MailEnviado = {
  id: "m1", plantilla_clave: "bienvenida", destinatario: "ana@k.com",
  asunto_render: "Bienvenida a Karstec", estado: "enviado", error: null,
  created_at: "2026-08-07T13:04:00+00:00",
}
const FALLIDO: MailEnviado = {
  id: "m2", plantilla_clave: "bienvenida", destinatario: "beto@k.com",
  asunto_render: "Bienvenida a Karstec", estado: "fallido",
  error: "el empleado no tiene email corporativo cargado",
  created_at: "2026-08-07T13:05:00+00:00",
}

/*
 * ⚠️ `filtrado: boolean` PASÓ A SER `chips: ChipFiltro[]` al migrar la tabla al patrón del bloque
 * B, y es el mismo dato con más información: antes la tabla sólo sabía SI había filtros puestos,
 * ahora sabe CUÁLES, y el vacío puede nombrarlos ("No hay mails con estado No entregados") en vez
 * de decir "ningún mail coincide con el filtro". Los tests de abajo pasan un chip de verdad donde
 * antes pasaban `true`.
 */
const CHIP = (etiqueta: string, valor: string): ChipFiltro =>
  ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

function render(props: Partial<Parameters<typeof HistorialTabla>[0]> = {}): string {
  const html = renderToStaticMarkup(
    <HistorialTabla
      items={props.items ?? []} cargando={props.cargando ?? false}
      error={props.error ?? false} chips={props.chips ?? []}
      onLimpiarTodo={() => {}} onReintentar={() => {}}
    />,
  )
  expect(html.length, "la tabla no renderizó nada: toda aserción de abajo sería vacua")
    .toBeGreaterThan(0)
  return html
}

describe("los tres estados son distinguibles", () => {
  it("🔴 con error dice que no se pudo cargar y ofrece reintentar", () => {
    const html = render({ error: true })

    expect(html).toContain(ERROR_HISTORIAL)
    expect(html).toContain("Reintentar")
  })

  it("🔴 y con error NUNCA aparece el texto de vacío", () => {
    const html = render({ error: true })

    expect(html).not.toContain(VACIO_HISTORIAL)
    expect(html).not.toContain("Ningún mail coincide")
  })

  it("🔴 sin datos y sin error, dice que todavía no se envió ninguno", () => {
    const html = render({ items: [] })

    expect(html).toContain(VACIO_HISTORIAL)
    expect(html).not.toContain(ERROR_HISTORIAL)
  })

  it("cargando no dice ni una cosa ni la otra: todavía no se sabe", () => {
    const html = render({ cargando: true })

    expect(html).not.toContain(VACIO_HISTORIAL)
    expect(html).not.toContain(ERROR_HISTORIAL)
    expect(html).toContain("animate-pulse")
  })

  it("el error gana sobre el cargando: no se muestran los dos a la vez", () => {
    expect(render({ error: true, cargando: true })).toContain(ERROR_HISTORIAL)
  })

  it("los dos textos son DISTINTOS (si se igualaran, todo lo de arriba sería vacuo)", () => {
    expect(ERROR_HISTORIAL).not.toBe(VACIO_HISTORIAL)
  })
})

describe("el vacío distingue «no hay nada» de «no hay nada con este filtro»", () => {
  it("con filtros puestos, el mensaje NOMBRA el filtro que dejó la tabla en cero", () => {
    const html = render({ items: [], chips: [CHIP("Estado", "No entregados")] })

    // Antes decía "Ningún mail coincide con el filtro": verdadero y sin decir cuál.
    expect(html).toContain("No hay mails con estado No entregados.")
    expect(html).not.toContain(VACIO_HISTORIAL)
    // Y ofrece la salida del patrón: quitar el filtro que se acaba de poner.
    expect(html).toContain("Quitar estado: No entregados")
  })

  it("sin filtros, habla de que no se envió nada — la salida del usuario es otra", () => {
    const html = render({ items: [], chips: [] })
    expect(html).toContain(VACIO_HISTORIAL)
    // 🔴 Y NO usa el genérico del patrón: nadie "carga" un mail enviado, lo produce el sistema.
    expect(html).not.toContain("Cuando se cargue el primero")
  })

  it("el encabezado sigue puesto en los tres estados: la tabla no cambia de forma", () => {
    for (const props of [{ items: [] }, { items: [ENVIADO] }, { cargando: true }]) {
      expect(render(props)).toContain("<thead")
    }
  })
})

describe("con datos se ve lo que se vino a buscar", () => {
  it("destinatario, plantilla y asunto de cada fila", () => {
    const html = render({ items: [ENVIADO] })

    expect(html).toContain("ana@k.com")
    expect(html).toContain("bienvenida")
    expect(html).toContain("Bienvenida a Karstec")
  })

  it("🔴 un fallido muestra el MOTIVO, que es la pregunta real («¿por qué no le llegó?»)", () => {
    const html = render({ items: [FALLIDO] })

    expect(html).toContain("No se entregó")
    expect(html).toContain("no tiene email corporativo")
  })

  it("un enviado NO muestra motivo ni la etiqueta de fallo", () => {
    // Contrapeso: sin esto, un componente que mostrara siempre "No se entregó" pasaría el de arriba.
    const html = render({ items: [ENVIADO] })

    expect(html).toContain("Enviado")
    expect(html).not.toContain("No se entregó")
  })

  it("la fecha se formatea legible, no ISO crudo", () => {
    const html = render({ items: [ENVIADO] })

    expect(html).toContain("07/08/2026")
    expect(html).not.toContain("2026-08-07T13:04")
  })

  it("una plantilla borrada no rompe la fila: muestra un guión", () => {
    // `plantilla_clave` es nullable en la tabla — el envío sobrevive a la plantilla.
    const html = render({ items: [{ ...ENVIADO, plantilla_clave: null }] })

    expect(html).toContain("—")
  })

  it("con datos no aparece ninguno de los dos vacíos", () => {
    const html = render({ items: [ENVIADO, FALLIDO] })

    expect(html).not.toContain(VACIO_HISTORIAL)
    expect(html).not.toContain(ERROR_HISTORIAL)
  })
})
