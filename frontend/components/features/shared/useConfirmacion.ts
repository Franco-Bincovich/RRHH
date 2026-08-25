"use client"

/**
 * El estado de una confirmación destructiva: qué fila está esperando el sí.
 *
 * 🔴 POR QUÉ UN HOOK Y NO `useState` EN CADA PANTALLA. Las cinco pantallas que se migraron el
 * 24/8/2026 tenían el borrado cableado igual —un `onDelete(id)` que sale directo al backend— y
 * meterle un diálogo a cada una a mano son cinco copias del mismo trío (pendiente, abrir, cerrar)
 * escritas por cinco personas distintas. El repo ya pagó esa forma dos veces: los 81 `<select>`
 * nativos con 29 constantes de estilo copiadas, y los 44 mensajes de error por campo con TRES
 * tamaños de letra distintos.
 *
 * 🔴 GUARDA EL ITEM ENTERO, NO EL ID. Es lo que hace posible la regla del copy: el texto tiene
 * que decir *"eliminar la ausencia de Ana Gómez del 3/3 al 7/3"*, y con un id suelto habría que
 * volver a buscar la fila en el array —que es justo lo que la pantalla ya no tiene garantizado
 * después de un refetch—. Con el objeto, el diálogo se explica con lo que tenía a mano cuando el
 * usuario apretó.
 *
 * ⚠️ NO tiene el `loading`: ése ya vive en la pantalla (`deletingId`, `cancelingId`) y duplicarlo
 * daría dos fuentes de verdad sobre el mismo botón. El hook expone `pendiente` y la pantalla
 * decide si eso está en curso.
 */
import { useCallback, useState } from "react"

export interface Confirmacion<T> {
  /** La fila esperando confirmación, o `null` si el diálogo está cerrado. */
  pendiente: T | null
  /** Abre el diálogo para esta fila. Es lo que va en el `onClick` del botón destructivo. */
  pedir: (item: T) => void
  /** Cierra sin hacer nada. Va en el `onClose` y en el botón Cancelar. */
  cerrar: () => void
  /** `true` mientras hay una fila esperando: alimenta el `open` de `ConfirmDialog`. */
  abierto: boolean
}

export function useConfirmacion<T>(): Confirmacion<T> {
  const [pendiente, setPendiente] = useState<T | null>(null)
  const pedir = useCallback((item: T) => setPendiente(item), [])
  const cerrar = useCallback(() => setPendiente(null), [])
  return { pendiente, pedir, cerrar, abierto: pendiente !== null }
}
