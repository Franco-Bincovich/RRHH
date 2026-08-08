import { describe, expect, it } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import { KanbanView } from "./KanbanView"
import type { Objetivo } from "@/types/objetivo"

/**
 * El kanban con jerarquía: los subobjetivos NO son tarjetas y NO suman al contador.
 *
 * 🔴 QUÉ CUBRE. Desde la migración 095 los hijos son filas de la misma tabla. Si se colaran al
 * tablero pasarían dos cosas a la vez: la columna se llenaría de tareas sueltas sin contexto, y
 * el número del encabezado —"8"— dejaría de decir cuántos OBJETIVOS hay para pasar a contar
 * objetivos y subtareas mezclados. El segundo efecto es el peligroso: no se ve.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS DATOS PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 *   1. 🔴 EL PADRE TIENE DOS HIJOS EN ESTADOS DISTINTOS AL SUYO. Si los hijos compartieran el
 *      estado del padre, "se filtran" y "no se filtran" cambiarían el mismo contador y no se
 *      podría saber cuál de las dos cosas pasó. Acá el padre está en `por_hacer` y sus hijos en
 *      `haciendo` y `terminado`: si se colaran, se verían en OTRAS columnas.
 *   2. 🔴 LOS HIJOS SE PASAN TAMBIÉN EN EL ARRAY DE PRIMER NIVEL, no solo anidados. El backend
 *      hoy devuelve solo raíces, así que un componente que confiara en eso pasaría el test sin
 *      filtrar nada. Pasarlos sueltos es lo que obliga al `if (!obj.parent_id)` a existir.
 *   3. Los títulos son distintos entre sí, así que se puede afirmar QUÉ tarjeta se renderizó y
 *      no solo cuántas.
 *
 * ⚠️ vitest corre con `environment: "node"` y sin jsdom: se verifica el MARKUP, no la
 * interacción. Los botones ← / → no se prueban acá.
 */

function obj(over: Partial<Objetivo> & { id: string; titulo: string }): Objetivo {
  return {
    empresa_id: "e-1", empresa_nombre: "Karstec",
    responsable_id: "u-1", responsable_nombre: "Ana Gómez",
    descripcion: null, prioridad: "media", estado: "por_hacer",
    fecha_entrega: null, created_at: "2026-01-05T09:00:00Z", updated_at: "2026-02-01T12:00:00Z",
    parent_id: null, parent_titulo: null,
    responsables: [{ id: "u-1", nombre: "Ana Gómez" }], hijos: [],
    ...over,
  }
}

const HIJO_1 = obj({ id: "h-1", titulo: "Relevar proveedores", estado: "haciendo", parent_id: "p-1", parent_titulo: "Migrar nómina" })
const HIJO_2 = obj({ id: "h-2", titulo: "Validar con contable", estado: "terminado", parent_id: "p-1", parent_titulo: "Migrar nómina" })
const PADRE = obj({ id: "p-1", titulo: "Migrar nómina", estado: "por_hacer", hijos: [HIJO_1, HIJO_2] })
const RAIZ = obj({ id: "r-1", titulo: "Auditar licencias", estado: "terminado" })

const noop = async () => {}

function render(objetivos: Objetivo[]) {
  return renderToStaticMarkup(
    <KanbanView
      objetivos={objetivos}
      onMover={noop}
      moviendo={null}
      canWrite={false}
      onEdit={() => {}}
      onDelete={() => {}}
      deletingId={null}
    />,
  )
}

describe("KanbanView con subobjetivos", () => {
  it("no renderiza a los hijos como tarjetas, ni siquiera si vienen sueltos en el array", () => {
    // Punto 2: se pasan anidados Y sueltos, que es el peor caso.
    const html = render([PADRE, HIJO_1, HIJO_2, RAIZ])

    expect(html).toContain("Migrar nómina")
    expect(html).toContain("Auditar licencias")
    expect(html).not.toContain("Relevar proveedores")
    expect(html).not.toContain("Validar con contable")
  })

  it("🔴 el contador de cada columna cuenta solo raíces", () => {
    const html = render([PADRE, HIJO_1, HIJO_2, RAIZ])

    // por_hacer: solo el padre. terminado: solo la raíz suelta (el hijo terminado no cuenta).
    // haciendo: ninguno — el único objetivo en ese estado es un hijo.
    const badges = [...html.matchAll(/<span[^>]*>(\d+)<\/span>/g)].map((m) => m[1])
    expect(badges).toEqual(["1", "0", "1"])
  })

  it("la columna vacía muestra su leyenda en vez de la tarjeta de un hijo", () => {
    const html = render([PADRE, HIJO_1, HIJO_2, RAIZ])

    expect(html).toContain("Sin objetivos")
  })

  it("el padre muestra cuántos subobjetivos tiene", () => {
    const html = render([PADRE])

    expect(html).toContain("2 subobjetivos")
  })

  it("una raíz sin hijos no muestra el badge", () => {
    const html = render([RAIZ])

    expect(html).not.toContain("subobjetivo")
  })

  it("contrapeso: sin jerarquía, las tarjetas se siguen renderizando", () => {
    // Si el filtro fuera demasiado agresivo (por ejemplo `!obj.hijos.length`), esto rojea.
    const html = render([RAIZ])

    expect(html).toContain("Auditar licencias")
  })
})
