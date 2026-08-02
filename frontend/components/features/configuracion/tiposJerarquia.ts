import type { TipoAusencia } from "@/types/ausencias"

/**
 * Ordena el catálogo plano en dos niveles: cada padre seguido de sus hijos.
 *
 * Función pura y aparte del componente para poder testearla sin renderizar nada — y porque el
 * orden es una regla, no markup: los hijos van DEBAJO de su padre aunque el backend los devuelva
 * ordenados por nombre (que es lo que hace, y por eso "Madre/padre" llegaría antes que
 * "Enfermedad familiar").
 *
 * ⚠️ Un hijo cuyo padre NO está en la lista se muestra igual, al final y sin indentar. Pasa en un
 * caso real: el padre puede ser un tipo DESACTIVADO (y la pantalla de configuración pide los
 * inactivos, pero el select del formulario no). Esconderlo lo volvería ineditable — que es peor
 * que mostrarlo fuera de lugar.
 */
export function ordenarPorJerarquia(tipos: TipoAusencia[]): Array<{ tipo: TipoAusencia; hijo: boolean }> {
  const padres = tipos.filter((t) => !t.padre_id)
  const porPadre = new Map<string, TipoAusencia[]>()
  for (const t of tipos) {
    if (!t.padre_id) continue
    porPadre.set(t.padre_id, [...(porPadre.get(t.padre_id) ?? []), t])
  }
  const salida = padres.flatMap((p) => [
    { tipo: p, hijo: false },
    ...(porPadre.get(p.id) ?? []).map((h) => ({ tipo: h, hijo: true })),
  ])
  const ubicados = new Set(salida.map((s) => s.tipo.id))
  return [...salida, ...tipos.filter((t) => !ubicados.has(t.id)).map((t) => ({ tipo: t, hijo: false }))]
}

/** Los que pueden ser padre: solo los de primer nivel (la jerarquía admite dos niveles). */
export function candidatosAPadre(tipos: TipoAusencia[]): TipoAusencia[] {
  return tipos.filter((t) => !t.padre_id && t.activo)
}
