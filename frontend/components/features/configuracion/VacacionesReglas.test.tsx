import { renderToStaticMarkup } from "react-dom/server"
import { Accordion } from "@base-ui/react/accordion"
import { describe, expect, it, vi } from "vitest"

import { VacacionesReglas } from "@/components/features/configuracion/VacacionesReglas"
import type { Parametros } from "@/types/configuracion"

/**
 * El bloque de reglas de vacaciones en SOLO LECTURA vs EDITABLE.
 *
 * Este es el escalón donde la distinción se puede verificar de verdad: el componente recibe
 * los datos POR PROPS, así que no depende de un efecto — y el proyecto corre vitest sin jsdom,
 * donde los efectos no se ejecutan. En page.test.tsx el bloque se queda cargando para siempre
 * y solo se puede mirar qué secciones aparecen, no qué hay adentro.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 * `editable` es la ÚNICA variable entre los dos casos: mismos params, mismos tramos. Si
 * alguien borra un `p.editable &&`, el botón aparece en el caso de solo lectura y rojea; si
 * lo deja siempre en false, desaparece del caso editable y también rojea. Y los campos se
 * afirman presentes en los DOS: solo lectura tiene que MOSTRAR el valor, no esconderlo — es
 * la diferencia con el criterio que se aplica a integraciones.
 */

const PARAMS: Parametros = {
  base_dias_habiles: 22,
  corte_antiguedad_mes: 10,
  periodo_vacacional_desde_mes: 10,
  periodo_vacacional_hasta_mes: 4,
  primer_anio_mes_corte: 7,
  primer_anio_dias: 5,
  vencimiento_anios: 4,
}

const TRAMOS = [
  { antiguedad_anios: 0, dias: 14 },
  { antiguedad_anios: 5, dias: 21 },
]

/**
 * El bloque es un Accordion.Item, así que necesita su Root — y el panel se abre EXPLÍCITAMENTE
 * con defaultValue. Sin abrirlo, Base UI no monta el contenido del panel y todas las
 * aserciones negativas de abajo pasarían por estar mirando un panel cerrado, no por el gate.
 * Los casos `editable` afirman en positivo justamente para dejar probado que el panel abrió.
 */
function render(editable: boolean, params: Parametros | null = PARAMS): string {
  return renderToStaticMarkup(
    <Accordion.Root defaultValue={["vacaciones"]} multiple>
      <VacacionesReglas
        params={params}
        fallback={<p>cargando</p>}
        onCampo={vi.fn()}
        tramos={TRAMOS}
        onTramos={vi.fn()}
        escalaPropia
        editable={editable}
        guardandoParams={false}
        guardandoEscala={false}
        onGuardarParams={vi.fn()}
        onGuardarEscala={vi.fn()}
      />
    </Accordion.Root>,
  )
}

describe("editable", () => {
  it("ofrece guardar las reglas y la escala", () => {
    const html = render(true)
    expect(html).toContain("Guardar reglas")
    expect(html).toContain("Guardar escala")
  })

  it("y permite agregar y quitar tramos", () => {
    const html = render(true)
    expect(html).toContain("Agregar tramo")
    expect(html).toContain("Quitar el tramo 1")
  })

  it("los campos no están deshabilitados", () => {
    // Se busca el ATRIBUTO renderizado (`disabled=""`), no la palabra suelta: las clases de
    // Tailwind traen `disabled:opacity-50` y un `toContain("disabled")` pasaría siempre.
    expect(render(true)).not.toContain('disabled=""')
  })
})

describe("solo lectura", () => {
  it("no ofrece ningún guardado", () => {
    const html = render(false)
    expect(html).not.toContain("Guardar reglas")
    expect(html).not.toContain("Guardar escala")
  })

  it("ni agregar ni quitar tramos", () => {
    const html = render(false)
    expect(html).not.toContain("Agregar tramo")
    expect(html).not.toContain("Quitar el tramo")
  })

  it("PERO muestra los valores, que es el punto de no ocultar el bloque", () => {
    // Un rol con lectura sobre los reportes necesita saber con qué reglas se calcularon.
    const html = render(false)
    expect(html).toContain("Mes de corte de antigüedad")
    expect(html).toContain("Vencimiento")
    expect(html).toContain('value="14"')   // el tramo de 0 años, visible
  })

  it("y los campos salen deshabilitados", () => {
    expect(render(false)).toContain('disabled=""')
  })
})

describe("el período vacacional se declara informativo", () => {
  it("la pantalla avisa que todavía no bloquea nada", () => {
    // Sin este aviso, alguien configura la ventana, asume que el sistema la hace cumplir, y
    // las licencias fuera de rango entran igual sin que nadie se entere.
    expect(render(true)).toContain("informativa")
  })
})

describe("estados sin datos", () => {
  it("cargando, el encabezado igual se renderiza", () => {
    // Devolver null entero haría aparecer y desaparecer bloques del acordeón mientras carga.
    const html = render(true, null)
    expect(html).toContain("Vacaciones")
    expect(html).toContain("cargando")
  })

  it("y no se muestran campos ni botones a medio cargar", () => {
    expect(render(true, null)).not.toContain("Guardar reglas")
  })
})
