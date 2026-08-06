import { toast } from "sonner"

import {
  designarRemitente as designarRemitenteApi,
  disconnectIntegracion,
  getGoogleAuthUrl,
  saveAnthropicKey,
  saveZernioKey,
} from "@/services/integraciones"

/** Cómo se nombra cada key en el mensaje de error, para que diga cuál falló. */
const ETIQUETA = { anthropic: "API", zernio: "Zernio" } as const

export type TipoKey = keyof typeof ETIQUETA

/*
 * Las tres escrituras de integraciones, sin React.
 *
 * Viven fuera del hook porque ninguna toca estado de React: llaman al backend, avisan el
 * error y piden recargar. `recargar` entra por parámetro en vez de importarse — la lista la
 * maneja el hook, y así estas funciones no dependen de él.
 */

/** Guarda la key. Devuelve si salió bien, para que el form se limpie solo entonces. */
export async function guardarKey(
  tipo: TipoKey,
  key: string,
  recargar: () => Promise<void>,
): Promise<boolean> {
  try {
    await (tipo === "anthropic" ? saveAnthropicKey : saveZernioKey)(key)
    await recargar()
    return true
  } catch {
    toast.error(`No se pudo guardar la clave de ${ETIQUETA[tipo]}. Intentá de nuevo.`)
    return false
  }
}

/**
 * Abre el popup de Google. El popup avisa que terminó por postMessage (OAuthPopupHandler),
 * así que acá no se recarga nada. Los errores propagan: sin auth_url no hay qué abrir.
 */
export async function conectarGoogle(): Promise<void> {
  const { auth_url } = await getGoogleAuthUrl()
  window.open(auth_url, "google_oauth", "width=600,height=700")
}

export async function desconectarGoogle(recargar: () => Promise<void>): Promise<void> {
  try {
    await disconnectIntegracion("google")
    await recargar()
  } catch {
    toast.error("No se pudo desconectar la cuenta de Google. Intentá de nuevo.")
  }
}

/**
 * Marca esta cuenta como la casilla del sistema. Se recarga porque el chip que la muestra sale
 * de `es_remitente_sistema`, que viene en la lista.
 */
export async function designarRemitente(recargar: () => Promise<void>): Promise<void> {
  try {
    await designarRemitenteApi()
    await recargar()
  } catch {
    toast.error("No se pudo designar la casilla del sistema. Intentá de nuevo.")
  }
}
