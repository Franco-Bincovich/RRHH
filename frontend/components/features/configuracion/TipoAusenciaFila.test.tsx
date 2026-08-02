import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { TipoAusenciaFila } from "@/components/features/configuracion/TipoAusenciaFila"
import type { TipoAusencia } from "@/types/ausencias"

/**
 * Una fila del catálogo de tipos de ausencia.
 *
 * 🔴 LO QUE ESTOS TESTS PROTEGEN ES LA PROMESA DEL BOTÓN. El tipo NO se borra nunca:
 * `solicitudes_ausencia.tipo_id` es una FK sin ON DELETE, así que borrarlo fallaría — y si no
 * fallara, se llevaría el historial de ausencias. Un botón que dijera "Eliminar" prometería
 * algo que no pasa, y el día que alguien lo cambie por costumbre, esto rojea.
 *
 * Componente presentacional puro: todo entra por props, así que sin jsdom se verifica igual.
 */

function tipo(over: Partial<TipoAusencia> = {}): TipoAusencia {
  return {
    id: "t1", nombre: "Enfermedad", es_base: false, activo: true,
    empresa_id: null, cuenta_ausentismo: true, ...over,
  }
}

function render(t: TipoAusencia, editable = true): string {
  return renderToStaticMarkup(
    <TipoAusenciaFila tipo={t} editable={editable} ocupado={false} onEditar={vi.fn()} />,
  )
}

describe("no hay borrado", () => {
  it("el botón dice 'Dar de baja', nunca 'Eliminar'", () => {
    const html = render(tipo())
    expect(html).toContain("Dar de baja")
    expect(html).not.toContain("Eliminar")
    expect(html).not.toContain("Borrar")
  })

  it("un tipo dado de baja ofrece reactivarse", () => {
    expect(render(tipo({ activo: false }))).toContain("Reactivar")
  })
})

describe("tipos base", () => {
  it("un tipo base activo no se puede dar de baja", () => {
    // Son el vocabulario mínimo con el que se cargó todo el histórico: sin ellos el
    // formulario de ausencias podría quedar sin una sola opción.
    expect(render(tipo({ es_base: true }))).toContain('disabled=""')
  })

  it("y se dice por qué, en vez de dejar un botón muerto", () => {
    expect(render(tipo({ es_base: true }))).toContain("Los tipos base no se pueden dar de baja")
  })

  it("uno NO base sí se puede dar de baja", () => {
    // La contracara: sin esto, el test de arriba pasaría con el botón siempre deshabilitado.
    expect(render(tipo({ es_base: false }))).not.toContain('disabled=""')
  })

  it("pero a un base sí se le puede cambiar si cuenta como ausentismo", () => {
    // El bloqueo es solo sobre la BAJA: el checkbox queda habilitado.
    // El espacio inicial del regex NO es decorativo — sin él, `data-disabled=""` (que el
    // botón deshabilitado también emite) contaría como un segundo elemento y el test
    // fallaría midiendo un atributo que no es el que importa.
    const html = render(tipo({ es_base: true }))
    expect(html).toContain("Cuenta como ausentismo")
    expect(html.match(/ disabled=""/g) ?? []).toHaveLength(1)  // solo el botón, no el checkbox
  })
})

describe("cuenta como ausentismo", () => {
  it("se muestra tildado cuando el tipo computa", () => {
    expect(render(tipo({ cuenta_ausentismo: true }))).toContain('checked=""')
  })

  it("y destildado cuando no", () => {
    expect(render(tipo({ cuenta_ausentismo: false }))).not.toContain('checked=""')
  })
})

describe("solo lectura", () => {
  it("sin permiso no aparece el botón de baja", () => {
    expect(render(tipo(), false)).not.toContain("Dar de baja")
  })

  it("pero el flag SIGUE VISIBLE: es información, no una acción", () => {
    expect(render(tipo(), false)).toContain("Cuenta como ausentismo")
  })
})

describe("origen del tipo", () => {
  it("un tipo global se marca como general", () => {
    expect(render(tipo({ empresa_id: null }))).toContain("General")
  })

  it("uno propio de la empresa no", () => {
    expect(render(tipo({ empresa_id: "emp-1" }))).not.toContain("General")
  })
})
