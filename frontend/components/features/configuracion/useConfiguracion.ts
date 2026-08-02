"use client"

import { useCallback, useEffect, useState } from "react"

import * as acciones from "@/components/features/configuracion/accionesConfiguracion"
import { useOcupado } from "@/components/features/configuracion/useOcupado"
import { fetchConfiguracion } from "@/services/configuracion"
import type { Configuracion, Parametros, TramoEscala } from "@/types/configuracion"

/**
 * Configuración vigente para la empresa activa, más sus dos guardados.
 *
 * `config` es lo que rige HOY (ya resuelto por COALESCE en el backend), no un borrador: el
 * borrador lo lleva el formulario. Tras guardar se RECARGA en vez de asumir lo enviado, porque
 * el guardado cambia algo que el cliente no sabe — una empresa que venía heredando pasa a
 * tener fila propia, y `es_propia` cambia de false a true.
 */
export function useConfiguracion() {
  const [config, setConfig] = useState<Configuracion | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const { ocupado, conBloqueo } = useOcupado()

  const load = useCallback(async () => {
    try {
      setConfig(await fetchConfiguracion())
      setError(false)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return {
    config,
    loading,
    error,
    ocupado,
    guardarParametros: (datos: Parametros) =>
      conBloqueo("parametros", () => acciones.guardarParametrosConAviso(datos, load)),
    guardarEscala: (tramos: TramoEscala[]) =>
      conBloqueo("escala", () => acciones.guardarEscalaConAviso(tramos, load)),
  }
}
