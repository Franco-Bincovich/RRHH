"use client"

import { useCallback, useEffect, useState } from "react"

import { borrarPlantilla, fetchPlantillas } from "@/services/plantillas"
import type { Plantilla } from "@/types/plantillas"

/**
 * Estado de las plantillas de mail de /configuracion: la lista y el catálogo de contextos.
 *
 * El catálogo viene del backend (no hardcodeado acá) para que la UI ofrezca EXACTAMENTE las
 * variables que el guardado va a aceptar. Duplicarlo en el front sería la misma regla escrita
 * dos veces — y divergiría en cuanto se agregue una variable.
 */
export function usePlantillas() {
  const [items, setItems] = useState<Plantilla[]>([])
  const [contextos, setContextos] = useState<Record<string, string[]>>({})
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const res = await fetchPlantillas()
      setItems(res.items)
      setContextos(res.contextos)
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  return {
    items,
    contextos,
    loading,
    recargar: load,
    borrar: async (id: string) => { await borrarPlantilla(id); await load() },
  }
}
