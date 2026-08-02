import type { TramoEscala } from "@/types/configuracion"

/**
 * Manipulación de la escala de antigüedad, en funciones PURAS y fuera del componente.
 *
 * Están acá y no dentro del `useState` del editor porque son la lógica que puede fallar
 * —duplicados, orden, el tramo que se agrega— y el proyecto corre vitest SIN jsdom: probadas
 * desde adentro del componente no se podrían ejercer. Acá se testean como lo que son.
 */

/** Los tramos ordenados por antigüedad, que es como se leen y como se aplican. */
export function ordenar(tramos: TramoEscala[]): TramoEscala[] {
  return [...tramos].sort((a, b) => a.antiguedad_anios - b.antiguedad_anios)
}

/**
 * Antigüedad sugerida para el próximo tramo: 5 años después del último.
 *
 * Sugerir 0 haría chocar con el tramo inicial casi siempre, y el usuario tendría que corregir
 * el campo antes de poder guardar en el caso más común.
 */
export function siguienteAntiguedad(tramos: TramoEscala[]): number {
  if (tramos.length === 0) return 0
  return Math.max(...tramos.map((t) => t.antiguedad_anios)) + 5
}

export function agregarTramo(tramos: TramoEscala[]): TramoEscala[] {
  const anios = siguienteAntiguedad(tramos)
  const ultimo = ordenar(tramos).at(-1)
  return ordenar([...tramos, { antiguedad_anios: anios, dias: ultimo ? ultimo.dias : 14 }])
}

export function quitarTramo(tramos: TramoEscala[], indice: number): TramoEscala[] {
  return tramos.filter((_, i) => i !== indice)
}

export function editarTramo(
  tramos: TramoEscala[],
  indice: number,
  campo: keyof TramoEscala,
  valor: number,
): TramoEscala[] {
  // NO reordena al editar: mover la fila bajo el cursor mientras se tipea la antigüedad haría
  // que el siguiente dígito caiga en otro tramo. El orden lo pone el backend al releer.
  return tramos.map((t, i) => (i === indice ? { ...t, [campo]: valor } : t))
}

/**
 * Antigüedades repetidas, si las hay.
 *
 * El backend las rechaza con 422 y la base tiene el índice único, pero avisar acá evita
 * mandar un guardado que se sabe que va a fallar — y señala CUÁL es el tramo repetido, que es
 * lo que el usuario necesita para arreglarlo.
 */
export function antiguedadesDuplicadas(tramos: TramoEscala[]): number[] {
  const vistas = new Set<number>()
  const repetidas = new Set<number>()
  for (const t of tramos) {
    if (vistas.has(t.antiguedad_anios)) repetidas.add(t.antiguedad_anios)
    vistas.add(t.antiguedad_anios)
  }
  return [...repetidas]
}
