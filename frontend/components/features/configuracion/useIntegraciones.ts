"use client"

import { useCallback, useEffect, useState } from "react"

import * as acciones from "@/components/features/configuracion/accionesIntegracion"
import type { TipoKey } from "@/components/features/configuracion/accionesIntegracion"
import { useOcupado } from "@/components/features/configuracion/useOcupado"
import { fetchIntegraciones } from "@/services/integraciones"
import type { Integracion } from "@/services/integraciones"

/**
 * Estado de las tres integraciones de /configuracion (Google, Anthropic, Zernio) y las
 * acciones ya envueltas en su bloqueo por botón.
 *
 * El listener de `message` vive acá y no en la página porque lo que tiene que reaccionar al
 * "el OAuth terminó" es esta lista: el popup avisa por postMessage y la recargamos.
 */
export function useIntegraciones() {
  const [integraciones, setIntegraciones] = useState<Integracion[]>([])
  const [loading, setLoading] = useState(true)
  const { ocupado, conBloqueo } = useOcupado()

  const load = useCallback(async () => {
    try {
      setIntegraciones(await fetchIntegraciones())
    } catch {
      // deja el estado desconectado si falla
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const onMessage = (e: MessageEvent<{ type: string; provider: string }>) => {
      if (e.origin !== window.location.origin) return
      if (e.data?.type === "oauth_complete" && e.data.provider === "google") load()
    }
    window.addEventListener("message", onMessage)
    return () => window.removeEventListener("message", onMessage)
  }, [load])

  return {
    loading,
    ocupado,
    google: integraciones.find((i) => i.tipo === "google"),
    anthropic: integraciones.find((i) => i.tipo === "anthropic"),
    zernio: integraciones.find((i) => i.tipo === "zernio"),
    guardarKey: (tipo: TipoKey, key: string) =>
      conBloqueo(tipo, () => acciones.guardarKey(tipo, key, load)),
    conectarGoogle: () => conBloqueo("google", acciones.conectarGoogle),
    desconectarGoogle: () => conBloqueo("google-off", () => acciones.desconectarGoogle(load)),
    designarRemitente: () =>
      conBloqueo("google-remitente", () => acciones.designarRemitente(load)),
  }
}
