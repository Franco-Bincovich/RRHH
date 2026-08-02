"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { useOcupado } from "@/components/features/configuracion/useOcupado"
import { createTipoAusencia, fetchTiposAusencia, updateTipoAusencia } from "@/services/ausencias"
import type { TipoAusencia, TipoAusenciaUpdate } from "@/types/ausencias"

/**
 * Catálogo de tipos de ausencia para la pantalla de configuración.
 *
 * Pide los INACTIVOS también: acá hay que verlos para poder reactivarlos. El select del
 * formulario de ausencias usa la lista por defecto, que los excluye.
 */
export function useTiposAusencia() {
  const [tipos, setTipos] = useState<TipoAusencia[]>([])
  const [loading, setLoading] = useState(true)
  const { ocupado, conBloqueo } = useOcupado()

  const load = useCallback(async () => {
    try {
      setTipos((await fetchTiposAusencia(true)).items)
    } catch {
      toast.error("No se pudieron cargar los tipos de ausencia.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const editar = (id: string, cambios: TipoAusenciaUpdate) =>
    conBloqueo(id, async () => {
      try {
        await updateTipoAusencia(id, cambios)
        await load()
        return true
      } catch (e) {
        // El backend explica el caso concreto (p. ej. "los tipos base no se pueden
        // desactivar"); el genérico es el último recurso.
        toast.error(e instanceof Error && e.message ? e.message : "No se pudo guardar el tipo.")
        return false
      }
    })

  const crear = (nombre: string, padreId?: string) =>
    conBloqueo("nuevo", async () => {
      try {
        await createTipoAusencia(nombre, padreId)
        await load()
        return true
      } catch (e) {
        toast.error(e instanceof Error && e.message ? e.message : "No se pudo crear el tipo.")
        return false
      }
    })

  return { tipos, loading, ocupado, editar, crear }
}
