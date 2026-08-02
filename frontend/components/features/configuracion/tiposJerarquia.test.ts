import { describe, expect, it } from "vitest"

import { candidatosAPadre, ordenarPorJerarquia } from "./tiposJerarquia"
import type { TipoAusencia } from "@/types/ausencias"

/**
 * El orden de dos niveles del catálogo (migración 088).
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 * La lista de entrada llega ORDENADA POR NOMBRE, que es como la devuelve el backend — y en ese
 * orden el hijo ("Madre/padre") viene ANTES que su padre ("Enfermedad familiar"). Con una
 * entrada ya agrupada, una función que no hiciera nada pasaría igual.
 */
function t(over: Partial<TipoAusencia> & { id: string; nombre: string }): TipoAusencia {
  return {
    es_base: false, activo: true, empresa_id: null, cuenta_ausentismo: true,
    padre_id: null, padre_nombre: null, ...over,
  }
}

// Ordenados por nombre, como llegan del backend: el hijo cae ANTES que el padre.
const CATALOGO = [
  t({ id: "h1", nombre: "Madre/padre", padre_id: "p1" }),
  t({ id: "p1", nombre: "Enfermedad familiar" }),
  t({ id: "p2", nombre: "Personal" }),
]

describe("ordenarPorJerarquia", () => {
  it("pone cada hijo DEBAJO de su padre, no donde lo dejó el orden alfabético", () => {
    expect(ordenarPorJerarquia(CATALOGO).map((x) => x.tipo.id)).toEqual(["p1", "h1", "p2"])
  })

  it("marca como hijo solo al que tiene padre", () => {
    expect(ordenarPorJerarquia(CATALOGO).map((x) => x.hijo)).toEqual([false, true, false])
  })

  it("un catálogo plano queda igual", () => {
    const planos = [t({ id: "a", nombre: "A" }), t({ id: "b", nombre: "B" })]
    expect(ordenarPorJerarquia(planos).map((x) => x.tipo.id)).toEqual(["a", "b"])
  })

  it("🔴 un hijo cuyo padre NO está en la lista se muestra igual, al final", () => {
    // Caso real: el padre está DESACTIVADO y el select no lo trae. Esconder al hijo lo volvería
    // ineditable, que es peor que mostrarlo fuera de lugar.
    const huerfano = [t({ id: "p2", nombre: "Personal" }),
                     t({ id: "h9", nombre: "Suelto", padre_id: "borrado" })]
    const salida = ordenarPorJerarquia(huerfano)
    expect(salida.map((x) => x.tipo.id)).toEqual(["p2", "h9"])
    expect(salida[1].hijo).toBe(false)
  })

  it("no pierde ni duplica ninguna fila", () => {
    expect(ordenarPorJerarquia(CATALOGO)).toHaveLength(CATALOGO.length)
  })
})

describe("candidatosAPadre", () => {
  it("ofrece SOLO tipos de primer nivel: así la profundidad 2 se respeta por construcción", () => {
    expect(candidatosAPadre(CATALOGO).map((x) => x.id)).toEqual(["p1", "p2"])
  })

  it("no ofrece un padre desactivado", () => {
    const conBaja = [...CATALOGO, t({ id: "p3", nombre: "Injustificada", activo: false })]
    expect(candidatosAPadre(conBaja).map((x) => x.id)).not.toContain("p3")
  })
})
