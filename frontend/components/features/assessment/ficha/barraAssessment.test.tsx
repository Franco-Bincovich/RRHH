import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { Button } from "@/components/ui/button"
import type { ResultadoDetalle } from "@/types/assessment"

import { BarraAssessment } from "./BarraAssessment"
import { datosClaveAssessment } from "./_datosClaveAssessment"

/**
 * La barra de identidad de la ficha del RESULTADO de un assessment: los cuatro datos clave, el
 * grupo de acciones y los chips.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDAN FALLAR?
 *   · (a) cuenta los `<dt>` del markup real: un quinto dato lo rojea aunque no pase por
 *     `datosClaveAssessment`.
 *   · (b) hoy esta ficha NO TIENE ninguna acción —los tres botones de descarga están
 *     deshabilitados y viven en su propio panel—, así que la aserción es que la barra no dibuje
 *     un grupo de acciones. Cuando la descarga exista (D2 del plan), este test rojea y obliga a
 *     escribir el orden. El segundo caso monta una acción de mentira y fija que caiga DESPUÉS del
 *     último dato clave, que es lo que la pone en el grupo de la derecha.
 *   · (c) los dos chips se comparan contra el relleno de marca: el score venía con
 *     `variant="default"` y volver a ponerlo mete `bg-primary` y rojea. Se verifica además que
 *     ninguno de los dos se pinte de verde o de rojo — un score coloreado afirma qué puntaje está
 *     bien, y eso no lo define el modelo.
 *   · (d) NO HAY TEST DE HISTORIAL ACÁ, y no es un olvido: un resultado de assessment es UNA
 *     medición fechada, no una serie. Lo que sería un historial —varias mediciones de la misma
 *     persona a lo largo del tiempo— no lo devuelve este endpoint y no hay pantalla que lo pida.
 *     El chip "Vigente" lo cubre `components/ui/Historial.test.tsx`.
 *
 * ⚠️ El módulo de assessment está APAGADO (`ASSESSMENT_ENABLED=false` y la página redirige antes
 * de renderizar), así que nada de esto se ve hoy en producción. El código está entero y estos
 * tests corren igual: prueban el componente, no la ruta.
 */

const BASE: ResultadoDetalle = {
  id: "r1",
  link_id: "l1",
  empresa_id: "e1",
  empresa_nombre: "Bodegas Tupungato",
  evaluado_nombre: "Ana Pérez",
  tipo: "completo",
  fecha_completado: "2026-05-14",
  perfil_dominante: "Analítico",
  score_general: 78,
  scores: { apertura: 80, responsabilidad: 70, estabilidad: 65 },
  area_nombre: "Sistemas",
  posicion_objetivo: "Líder técnico",
}

const barra = (resultado: ResultadoDetalle, acciones?: React.ReactNode) =>
  renderToStaticMarkup(<BarraAssessment resultado={resultado} acciones={acciones} />)

describe("(a) la barra del assessment muestra EXACTAMENTE cuatro datos clave", () => {
  it("cuatro, ni tres ni cinco", () => {
    expect(datosClaveAssessment(BASE)).toHaveLength(4)
    expect(barra(BASE).match(/<dt/g) ?? []).toHaveLength(4)
  })

  it("son empresa, área, posición objetivo y completado", () => {
    expect(datosClaveAssessment(BASE).map((d) => d.label)).toEqual([
      "Empresa", "Área", "Posición objetivo", "Completado",
    ])
  })

  it("el tipo NO gasta uno de los cuatro: va bajo el nombre", () => {
    expect(barra(BASE)).toContain("Assessment completo")
    expect(datosClaveAssessment(BASE).map((d) => d.label)).not.toContain("Tipo")
  })

  it("una campaña sin posición objetivo lo dice: es una decisión, no un dato faltante", () => {
    expect(datosClaveAssessment({ ...BASE, posicion_objetivo: null })[2].valor).toBe("Sin definir")
  })

  it("un link enviado y sin responder dice 'Sin completar', no una fecha en blanco", () => {
    expect(datosClaveAssessment({ ...BASE, fecha_completado: null })[3].valor).toBe("Sin completar")
    expect(datosClaveAssessment(BASE)[3].valor).toBe("14/05/2026")
  })

  it("las migas llevan a Assessment y la actual no es link", () => {
    const html = barra(BASE)
    expect(html).toContain('href="/assessment"')
    expect(html).toContain('aria-current="page"')
  })
})

describe("(b) la acción primaria es la última del grupo", () => {
  it("hoy la ficha no tiene ninguna acción", () => {
    expect(barra(BASE).match(/<button/g) ?? []).toHaveLength(0)
  })

  it("cuando tenga una, cae después del último dato clave", () => {
    const html = barra(BASE, <Button className="min-h-11">Descargar</Button>)
    expect(html.indexOf("Descargar")).toBeGreaterThan(html.lastIndexOf("Posición objetivo"))
  })
})

describe("(c) los chips no usan variant=default", () => {
  it("perfil y score usan el par neutro y ninguno el relleno de marca", () => {
    const html = barra(BASE)
    expect(html).toContain("Analítico")
    expect(html).toContain("Score general 78")
    expect(html).toContain("bg-secondary")
    expect(html).not.toContain("bg-primary")
  })

  it("el score no se pinta de bueno ni de malo", () => {
    // Un score verde o rojo afirma qué puntaje está bien. Ni el modelo ni el producto lo definen.
    for (const score of [12, 50, 99]) {
      const html = barra({ ...BASE, score_general: score })
      expect(html, `score ${score} pinta juicio`).not.toContain("bg-success-wash")
      expect(html, `score ${score} pinta juicio`).not.toContain("bg-danger-wash")
    }
  })

  it("sin perfil ni score no dibuja chips vacíos", () => {
    const html = barra({ ...BASE, perfil_dominante: null, score_general: null })
    expect(html).not.toContain("Score general")
    expect(html).not.toContain("Analítico")
  })

  it("un score de 0 SÍ se muestra: es un valor, no un vacío", () => {
    // `score_general != null` y no un truthy: con `!` un cero desaparecería de la pantalla.
    expect(barra({ ...BASE, score_general: 0 })).toContain("Score general 0")
  })
})
