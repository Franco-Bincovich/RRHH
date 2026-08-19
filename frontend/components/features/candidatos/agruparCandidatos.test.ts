import { describe, expect, it } from "vitest"

import { agruparCandidatos } from "./agruparCandidatos"
import type { CandidatoConGrupo } from "@/types/candidato"

/**
 * El agrupamiento ocurre DENTRO de la página (el listado se pagina plano), así que el conteo del
 * encabezado no puede salir de acá: llega del backend en `conteo_por_grupo`.
 *
 * 🔴 QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR: que la página y el conteo
 * coincidieran. Por eso todas las fixturas de acá tienen MENOS filas de las que declara el
 * conteo — si fueran iguales, `totalGrupo` y `candidatos.length` darían lo mismo y un
 * `totalGrupo = candidatos.length` (el bug que estos tests cubren) pasaría verde.
 */

function candidato(id: string, grupo: string | null, activa = true): CandidatoConGrupo {
  return {
    id, vacante_id: grupo ? "v1" : null, nombre: `N${id}`, apellido: "Prueba",
    email: `${id}@x.com`, telefono: null, cargo_anterior: null, empresa_anterior: null,
    etapa_pipeline: "postulado", estado: "activo", score_ia: null, busqueda_congelada: null,
    cv_storage_path: null,
    screening_warning: null, clasificacion_ia: null, clasificacion_motivo: null,
    clasificacion_origen: null, created_at: "2026-08-01T09:00:00",
    grupo_nombre: grupo, busqueda_activa: activa,
  }
}

describe("agruparCandidatos — el conteo del encabezado", () => {
  it("toma el total del backend, no el largo de la página", () => {
    const pagina = [candidato("1", "Analista SSR"), candidato("2", "Analista SSR")]

    const [grupo] = agruparCandidatos(pagina, { "Analista SSR": 28 })

    expect(grupo.candidatos).toHaveLength(2)
    expect(grupo.totalGrupo).toBe(28)
  })

  it("el mismo grupo da el mismo total con páginas distintas", () => {
    const conteo = { "Analista SSR": 28 }
    const p1 = [candidato("1", "Analista SSR"), candidato("2", "Analista SSR")]
    const p2 = [candidato("3", "Analista SSR")]

    expect(agruparCandidatos(p1, conteo)[0].totalGrupo)
      .toBe(agruparCandidatos(p2, conteo)[0].totalGrupo)
  })

  it("cae al largo visible cuando el backend no mandó la clave", () => {
    // El literal "Sin búsqueda" está duplicado entre Python y TS y no hay test que lo ate. Si
    // divergen, el grupo cae acá: muestra un número menor pero cierto, nunca uno inventado.
    const [grupo] = agruparCandidatos([candidato("1", null, false)], { Otra: 9 })

    expect(grupo.nombre).toBe("Sin búsqueda")
    expect(grupo.totalGrupo).toBe(1)
  })

  it("sin conteo (llamada sin el segundo argumento) no rompe ni inventa", () => {
    const [grupo] = agruparCandidatos([candidato("1", "X"), candidato("2", "X")])

    expect(grupo.totalGrupo).toBe(2)
    expect(Number.isNaN(grupo.totalGrupo)).toBe(false)
  })

  it("un grupo cuyo total es 0 en el conteo no se confunde con 'sin dato'", () => {
    // `?? ` y no `||`: con `||`, un 0 legítimo caería al fallback y mostraría el largo visible.
    // El caso no es teórico — pasa apenas el backend devuelva una clave con 0.
    const [grupo] = agruparCandidatos([candidato("1", "X")], { X: 0 })

    expect(grupo.totalGrupo).toBe(0)
  })
})

describe("agruparCandidatos — lo que ya hacía", () => {
  it("pone las búsquedas activas antes que las cerradas", () => {
    const items = [candidato("1", "Cerrada", false), candidato("2", "Viva", true)]

    expect(agruparCandidatos(items, {}).map((g) => g.nombre)).toEqual(["Viva", "Cerrada"])
  })

  it("un grupo es activo si AL MENOS uno de sus candidatos lo es", () => {
    const items = [candidato("1", "X", false), candidato("2", "X", true)]

    expect(agruparCandidatos(items, {})[0].activa).toBe(true)
  })
})
