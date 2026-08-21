import type { Objetivo } from "@/types/objetivo"

/**
 * Las tres funciones puras con las que la vista Lista arma sus filas. Salieron de `ListView.tsx`
 * al migrarla al patrón del bloque B: con el esqueleto y el vacío nuevos, el archivo pasaba de
 * las 150 líneas. Son puras, así que además se pueden testear sin renderizar.
 */

export function formatDate(s: string | null): string {
  if (!s) return "—"
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y}`
}

/**
 * Una entrega vencida es la que tiene fecha pasada Y no está terminada. Las dos condiciones
 * importan: sin la segunda, todo lo que se entregó a tiempo el mes pasado aparecería en rojo
 * para siempre.
 */
export function isOverdue(fecha: string | null, estado: string): boolean {
  return !(!fecha || estado === "terminado") && fecha < new Date().toISOString().slice(0, 10)
}

/**
 * Árbol → filas: cada raíz seguida de sus hijos, marcados para indentar.
 *
 * 🔴 Los hijos van EN LA MISMA TABLA e indentados, no en una tabla aparte ni colapsados: la
 * vista de Lista es donde alguien busca "qué hay que hacer y para cuándo", y la fecha de
 * entrega real vive en los subobjetivos. Esconderlos detrás de un expandir dejaría la columna
 * más importante fuera de la vista por default.
 *
 * 🔴 Y ES LA RAZÓN POR LA QUE EL PIE NO DICE "N FILAS": esta función devuelve raíces + hijos, así
 * que casi siempre hay más renglones que objetivos principales. El pie cuenta raíces, que es lo
 * que el backend sabe contar.
 *
 * No recursiona: la profundidad máxima es 2 (services/_objetivos_jerarquia.py).
 */
export function aplanar(raices: Objetivo[]): { obj: Objetivo; esHijo: boolean }[] {
  return raices.flatMap((r) => [
    { obj: r, esHijo: false },
    ...r.hijos.map((h) => ({ obj: h, esHijo: true })),
  ])
}
