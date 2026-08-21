import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import type { OnboardingTemplate, TemplateTarea } from "@/types/onboarding"

import { VisibilidadToggle } from "../VisibilidadToggle"
import { BarraTemplate } from "./BarraTemplate"
import { datosClaveTemplate } from "./_datosClaveTemplate"

/**
 * La barra de identidad de la ficha de un TEMPLATE de onboarding: los cuatro datos clave, el
 * orden de las acciones y el chip de visibilidad.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDAN FALLAR?
 *   · (a) cuenta los `<dt>` del markup real. Un quinto dato lo rojea aunque no pase por
 *     `datosClaveTemplate`.
 *   · (b) acá NO se pueden contar los `<button>` como en las otras fichas: el título y el
 *     subtítulo son editables en el lugar y aportan dos botones propios adentro del bloque de
 *     identidad. Por eso la aserción compara POSICIONES: la acción tiene que aparecer DESPUÉS del
 *     último dato clave, que es lo que la pone en el grupo de la derecha y no entre los datos.
 *   · (c) el chip se compara contra los pares semánticos y contra el relleno de marca: pintarlo
 *     con `variant="default"` mete `bg-primary` y rojea. Ojo: el botón de guardar de la edición
 *     en línea también trae `bg-primary`, pero sólo cuando está en modo edición, y
 *     `renderToStaticMarkup` no ejecuta `useState`, así que nunca sale en este markup.
 *   · (d) NO HAY TEST DE HISTORIAL ACÁ, y no es un olvido: un template no tiene ninguno. El
 *     modelo guarda el plan vigente y nada de cómo llegó a serlo — no hay tabla de versiones ni
 *     de cambios. El chip "Vigente" lo cubre `components/ui/Historial.test.tsx`.
 */

const tarea = (id: string, semana: number): TemplateTarea => ({
  id, template_id: "t1", titulo: `Tarea ${id}`, descripcion: null, semana, orden: 1,
})

const BASE: OnboardingTemplate = {
  id: "t1",
  nombre: "Ingreso Sistemas",
  empresa_id: "e1",
  empresa_nombre: "Bodegas Tupungato",
  descripcion: "Plan estándar para perfiles técnicos",
  created_by: "u1",
  created_by_nombre: "Ana Pérez",
  es_publica: true,
  tareas: [tarea("a", 1), tarea("b", 1), tarea("c", 2), tarea("d", 3)],
  tareas_total: 4,
}

const noop = async () => {}
const barra = (template: OnboardingTemplate, canWrite = false, acciones?: React.ReactNode) =>
  renderToStaticMarkup(
    <BarraTemplate template={template} canWrite={canWrite} onGuardarCampo={noop} acciones={acciones} />,
  )

describe("(a) la barra del template muestra EXACTAMENTE cuatro datos clave", () => {
  it("cuatro, ni tres ni cinco", () => {
    expect(datosClaveTemplate(BASE)).toHaveLength(4)
    expect(barra(BASE).match(/<dt/g) ?? []).toHaveLength(4)
  })

  it("son empresa, autor, tareas y semanas con tareas", () => {
    expect(datosClaveTemplate(BASE).map((d) => d.label)).toEqual([
      "Empresa", "Autor", "Tareas", "Semanas con tareas",
    ])
  })

  it("las tareas salen de `tareas_total` del backend, no del largo del array", () => {
    // El array de esta ficha trae las tareas para pintarlas; el número lo dice el backend. Si
    // alguna vez llegan parciales, contar el array diría menos de las que hay.
    const parcial = { ...BASE, tareas_total: 12 }
    expect(datosClaveTemplate(parcial)[2].valor).toBe("12")
  })

  it("las semanas con tareas se cuentan sobre las que TIENEN, no sobre las que existen", () => {
    expect(datosClaveTemplate(BASE)[3].valor).toBe("3 de 4")
    expect(datosClaveTemplate({ ...BASE, tareas: [] })[3].valor).toBe("0 de 4")
    expect(datosClaveTemplate({ ...BASE, tareas: [tarea("a", 1), tarea("b", 1)] })[3].valor).toBe("1 de 4")
  })

  it("un template sin empresa dice que sirve para todas, no una raya", () => {
    expect(datosClaveTemplate({ ...BASE, empresa_nombre: null })[0].valor).toBe("Todas las empresas")
  })

  it("una plantilla huérfana lo dice: es la que cualquiera puede cambiar", () => {
    expect(datosClaveTemplate({ ...BASE, created_by_nombre: null })[1].valor).toBe("Sin autor")
  })

  it("la descripción NO gasta uno de los cuatro: va bajo el nombre", () => {
    expect(barra(BASE)).toContain("Plan estándar para perfiles técnicos")
    expect(datosClaveTemplate(BASE).map((d) => d.label)).not.toContain("Descripción")
  })

  it("las migas llevan a Templates y la actual no es link", () => {
    const html = barra(BASE)
    expect(html).toContain('href="/onboarding/templates"')
    expect(html).toContain('aria-current="page"')
  })
})

describe("(b) la acción primaria es la última del grupo", () => {
  it("la acción va DESPUÉS del último dato clave", () => {
    // Se monta el control REAL, no un botón de mentira: es el único de la ficha y lo que se
    // verifica es dónde queda. Se lo ancla por `aria-pressed`, que es suyo y que el chip no
    // tiene — buscar el texto "Compartida" habría encontrado primero el chip, que dice lo mismo.
    const html = barra(BASE, true, (
      <VisibilidadToggle templateId="t1" esPublica puedeCambiar onCambiada={() => {}} />
    ))
    expect(html).toContain("aria-pressed")
    expect(html.indexOf("aria-pressed")).toBeGreaterThan(html.lastIndexOf("Semanas con tareas"))
  })

  it("sin permiso de escritura la barra no dibuja acciones, pero el chip sigue estando", () => {
    const html = barra(BASE)
    // El chip es el ESTADO y está siempre: sin él, un rol de sólo lectura no tendría forma de
    // saber que una plantilla es privada.
    expect(html).toContain("Compartida")
    expect(barra({ ...BASE, es_publica: false })).toContain("Privada")
  })

  it("sin permiso de escritura el nombre no es un botón de edición", () => {
    // `InlineEdit` degrada a texto plano con `canEdit={false}`. Si eso se rompiera, un rol de
    // lectura abriría el editor y recién fallaría al guardar.
    expect(barra(BASE).match(/<button/g) ?? []).toHaveLength(0)
    expect(barra(BASE, true).match(/<button/g) ?? []).toHaveLength(2)
  })
})

describe("(c) el chip de visibilidad no usa variant=default", () => {
  it("privada es atención, compartida es neutro, ninguna es el relleno de marca", () => {
    expect(barra({ ...BASE, es_publica: false })).toContain("bg-warning-wash")
    expect(barra(BASE)).toContain("bg-secondary")
    for (const es_publica of [true, false]) {
      expect(barra({ ...BASE, es_publica }), `es_publica=${es_publica} pinta bg-primary`)
        .not.toContain("bg-primary")
    }
  })
})
