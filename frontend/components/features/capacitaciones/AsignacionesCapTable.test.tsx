import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { AsignacionesCapTable } from "@/components/features/capacitaciones/AsignacionesCapTable"
import type { Asignacion } from "@/types/capacitacion"

/**
 * La fila SIN empleado vinculado (migración 116: el import de formación carga los nombres que no
 * matchean con `nombre_libre` y `empleado_id` en NULL).
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * **1. LAS DOS FILAS EN EL MISMO RENDER.** Con una sola, "muestra la marca" y "muestra la marca
 * siempre" dan el mismo markup, y un componente que la pusiera en TODAS las filas pasaría igual.
 * El fixture trae una vinculada y una suelta, y se afirma que la marca aparece UNA sola vez.
 *
 * **2. LA GUARDA DE MARKUP NO VACÍO.** El proyecto corre vitest SIN jsdom y se renderiza a
 * string: si el componente devolviera "" —porque revienta, porque cambia a `return null`— toda
 * aserción NEGATIVA pasaría sobre la nada. Por eso el render pasa por `_render`.
 *
 * **3. EL NOMBRE SE BUSCA EN EL MARKUP, NO EN EL FIXTURE.** Los dos nombres son distintos entre
 * sí, así que "muestra el nombre libre" no puede colarse mostrando el otro.
 *
 * ⚠️ `renderToStaticMarkup` NO ejecuta `useEffect`: acá alcanza porque la tabla es puramente
 * presentacional (no pide datos). En un componente con fetch, este molde NO probaría el guard.
 */

const VINCULADA: Asignacion = {
  id: "a1", empresa_id: "e1", empresa_nombre: "Karstec",
  capacitacion_id: "c1", capacitacion_nombre: "Higiene y seguridad",
  empleado_id: "emp1", empleado_nombre: "Ana Gómez", nombre_libre: null,
  area_id: "ar1", area_nombre: "Sistemas", estado: "completado",
  fecha_asignacion: null, fecha_limite: null, fecha_completado: null,
  certificado_url: null, created_at: "2026-08-13T10:00:00Z",
}

// La fila que hoy no puede existir y mañana sí: sin empleado, con el nombre crudo del Excel.
const SUELTA: Asignacion = {
  ...VINCULADA, id: "a2",
  empleado_id: null, empleado_nombre: null, nombre_libre: "Perez Juan",
  area_id: null, area_nombre: null,
}

const PROPS = {
  loading: false, error: false, canWrite: false, mostrarEmpresa: false,
  deletingId: null, onReload: () => {}, onEditarEstado: () => {}, onEliminar: () => {},
}

function _render(asignaciones: Asignacion[]): string {
  const html = renderToStaticMarkup(<AsignacionesCapTable {...PROPS} asignaciones={asignaciones} />)
  // 🔴 GUARDA: sin esto, un componente que devuelve "" pasa todas las aserciones negativas.
  expect(html.length).toBeGreaterThan(80)
  return html
}

describe("AsignacionesCapTable — filas sin empleado vinculado", () => {
  it("muestra el nombre libre de la fila que no tiene empleado", () => {
    const html = _render([VINCULADA, SUELTA])

    // 🔴 Se ancla a la CELDA del empleado (`font-medium`) y no al markup entero: el guion de
    // "sin dato" aparece de todas formas en las columnas de fecha, así que un `not.toContain("—")`
    // suelto sería imposible de satisfacer y diría otra cosa que la que se quiere afirmar.
    expect(html).toContain('font-medium">Perez Juan')
    expect(html).not.toContain('font-medium">—')  // no cae al guion: el nombre existe, suelto
  })

  it("marca esa fila como no vinculada, y SOLO esa", () => {
    const html = _render([VINCULADA, SUELTA])

    expect(html).toContain("Sin vincular")
    expect(html.match(/Sin vincular/g)).toHaveLength(1)
    expect(html).toContain("Ana Gómez")
  })

  it("un listado sin filas sueltas no muestra ninguna marca", () => {
    // 🔴 EL CONTRASTE: sin esto, un componente que pusiera la marca siempre pasaría el de arriba
    // en cuanto alguien agregara una segunda fila vinculada.
    const html = _render([VINCULADA])

    expect(html).toContain("Ana Gómez")
    expect(html).not.toContain("Sin vincular")
  })
})
