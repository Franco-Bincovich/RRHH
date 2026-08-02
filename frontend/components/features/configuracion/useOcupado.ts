"use client"

import { useCallback, useState } from "react"

/**
 * Lleva la cuenta de qué acciones están en vuelo, por clave.
 *
 * Es un MAPA y no un booleano único a propósito: con un solo flag, arrancar una acción
 * mientras otra corre rehabilitaría el botón de la primera, y el `finally` de la que
 * termine antes apagaría el spinner de la otra. Cada botón se deshabilita solo.
 */
export function useOcupado() {
  const [ocupado, setOcupado] = useState<Record<string, boolean>>({})

  /** Corre `fn` con `clave` marcada como ocupada, y la libera pase lo que pase. */
  const conBloqueo = useCallback(async <T,>(clave: string, fn: () => Promise<T>): Promise<T> => {
    setOcupado((p) => ({ ...p, [clave]: true }))
    try {
      return await fn()
    } finally {
      setOcupado((p) => ({ ...p, [clave]: false }))
    }
  }, [])

  return { ocupado, conBloqueo }
}
