import { describe, expect, it } from "vitest"

import {
  agregarTramo, antiguedadesDuplicadas, editarTramo, ordenar, quitarTramo, siguienteAntiguedad,
} from "@/components/features/configuracion/escala"

/**
 * La escala de antigüedad es una LISTA que se edita desde la UI, y estas son las funciones
 * que la manipulan.
 *
 * Están fuera del componente justamente para poder probarlas: el proyecto corre vitest SIN
 * jsdom, así que agregar o quitar un tramo desde adentro del componente no se puede ejercer
 * —no hay clicks—. Acá son funciones puras y se verifican como tales.
 *
 * 🚨 Todas son PURAS y no mutan la entrada; hay un test explícito para eso. Si alguna pasara
 * a mutar, el `useState` del editor dejaría de re-renderizar (misma referencia) y la pantalla
 * se congelaría sin ningún error visible.
 */

const BASE = [
  { antiguedad_anios: 0, dias: 14 },
  { antiguedad_anios: 5, dias: 21 },
  { antiguedad_anios: 15, dias: 28 },
]

describe("agregar", () => {
  it("suma un tramo", () => {
    expect(agregarTramo(BASE)).toHaveLength(4)
  })

  it("lo sugiere 5 años después del último, no en 0", () => {
    // Sugerir 0 chocaría con el tramo inicial casi siempre, y habría que corregir el campo
    // antes de poder guardar en el caso más común.
    expect(agregarTramo(BASE).at(-1)?.antiguedad_anios).toBe(20)
  })

  it("sobre una escala vacía arranca en 0", () => {
    expect(agregarTramo([])).toEqual([{ antiguedad_anios: 0, dias: 14 }])
  })

  it("hereda los días del último tramo, que es el punto de partida más probable", () => {
    expect(agregarTramo(BASE).at(-1)?.dias).toBe(28)
  })

  it("el resultado sale ordenado", () => {
    const desordenado = [{ antiguedad_anios: 10, dias: 25 }, { antiguedad_anios: 0, dias: 14 }]
    expect(agregarTramo(desordenado).map((t) => t.antiguedad_anios)).toEqual([0, 10, 15])
  })
})

describe("quitar", () => {
  it("saca el tramo del índice pedido", () => {
    expect(quitarTramo(BASE, 1).map((t) => t.antiguedad_anios)).toEqual([0, 15])
  })

  it("se pueden quitar todos: eso es volver a heredar la escala general", () => {
    let t = BASE
    for (let i = BASE.length - 1; i >= 0; i--) t = quitarTramo(t, i)
    expect(t).toEqual([])
  })

  it("quita por ÍNDICE y no por antigüedad", () => {
    // Con dos tramos duplicados (estado transitorio válido mientras se edita), quitar por
    // antigüedad se llevaría los dos y el usuario perdería el que quería conservar.
    const conDup = [
      { antiguedad_anios: 5, dias: 21 },
      { antiguedad_anios: 5, dias: 28 },
    ]
    expect(quitarTramo(conDup, 0)).toEqual([{ antiguedad_anios: 5, dias: 28 }])
  })
})

describe("editar", () => {
  it("cambia solo el tramo tocado", () => {
    const r = editarTramo(BASE, 1, "dias", 25)
    expect(r[1].dias).toBe(25)
    expect(r[0].dias).toBe(14)
    expect(r[2].dias).toBe(28)
  })

  it("NO reordena mientras se edita la antigüedad", () => {
    // Reordenar movería la fila bajo el cursor y el siguiente dígito caería en otro tramo:
    // tipear "20" sobre el tramo de 0 pasaría por el estado intermedio "2".
    const r = editarTramo(BASE, 0, "antiguedad_anios", 20)
    expect(r.map((t) => t.antiguedad_anios)).toEqual([20, 5, 15])
  })
})

describe("duplicados", () => {
  it("no hay ninguno en una escala sana", () => {
    expect(antiguedadesDuplicadas(BASE)).toEqual([])
  })

  it("detecta la antigüedad repetida y dice CUÁL", () => {
    // El backend la rechaza con 422 y la base tiene el índice único; avisar acá evita mandar
    // un guardado que se sabe que va a fallar, y señala el tramo a corregir.
    const conDup = [...BASE, { antiguedad_anios: 5, dias: 30 }]
    expect(antiguedadesDuplicadas(conDup)).toEqual([5])
  })

  it("no repite la misma antigüedad en el aviso aunque esté tres veces", () => {
    const triple = [
      { antiguedad_anios: 5, dias: 21 },
      { antiguedad_anios: 5, dias: 22 },
      { antiguedad_anios: 5, dias: 23 },
    ]
    expect(antiguedadesDuplicadas(triple)).toEqual([5])
  })
})

describe("ordenar y sugerir", () => {
  it("ordena por antigüedad ascendente", () => {
    const desordenado = [{ antiguedad_anios: 15, dias: 28 }, { antiguedad_anios: 0, dias: 14 }]
    expect(ordenar(desordenado).map((t) => t.antiguedad_anios)).toEqual([0, 15])
  })

  it("la sugerencia mira el MÁXIMO, no el último del array", () => {
    const desordenado = [{ antiguedad_anios: 15, dias: 28 }, { antiguedad_anios: 0, dias: 14 }]
    expect(siguienteAntiguedad(desordenado)).toBe(20)
  })
})

describe("pureza", () => {
  it("ninguna muta el array que recibe", () => {
    // Si mutaran, el useState del editor recibiría la MISMA referencia, React no
    // re-renderizaría y la pantalla se congelaría sin ningún error visible.
    const original = BASE.map((t) => ({ ...t }))
    agregarTramo(BASE)
    quitarTramo(BASE, 0)
    editarTramo(BASE, 0, "dias", 99)
    ordenar(BASE)
    expect(BASE).toEqual(original)
  })
})
