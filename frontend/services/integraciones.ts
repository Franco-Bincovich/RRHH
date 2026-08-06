import { apiFetch } from "@/services/api"

export interface Integracion {
  tipo: string
  email_cuenta: string | null
  activo: boolean
  connected: boolean
  /**
   * ¿La cuenta tiene el permiso de ENVIAR mails (scope `gmail.send`)?
   *
   * Va aparte de `connected` porque son cosas distintas: una cuenta conectada antes de que
   * existiera ese scope sigue leyendo el buzón perfectamente y no puede mandar nada. Google no
   * amplía un consentimiento ya dado, así que hay que reconectar — y esto es lo que permite
   * decirlo ANTES, en vez de que el usuario se entere por un 403 en medio de un envío.
   */
  puede_enviar: boolean
  /** ¿Es la casilla desde la que salen los mails del sistema? */
  es_remitente_sistema: boolean
}

export async function fetchIntegraciones(): Promise<Integracion[]> {
  return apiFetch<Integracion[]>("/api/integraciones")
}

export async function getGoogleAuthUrl(): Promise<{ auth_url: string }> {
  return apiFetch<{ auth_url: string }>("/api/integraciones/google/auth")
}

export async function saveAnthropicKey(api_key: string): Promise<Integracion> {
  return apiFetch<Integracion>("/api/integraciones/anthropic", {
    method: "POST",
    body: JSON.stringify({ api_key }),
  })
}

export async function disconnectIntegracion(tipo: string): Promise<void> {
  await apiFetch<void>(`/api/integraciones/${tipo}`, { method: "DELETE" })
}

/**
 * Designa la cuenta de Google del usuario como la casilla desde la que salen los mails del
 * sistema. Sin body: el backend toma la identidad del token, no de un parámetro.
 *
 * No existe la operación inversa a propósito: la casilla es única y se cambia designando otra.
 * Sin casilla configurada, todo envío corta con `MAIL_SIN_REMITENTE`.
 */
export async function designarRemitente(): Promise<void> {
  await apiFetch<Integracion>("/api/integraciones/google/remitente", { method: "POST" })
}

export async function saveZernioKey(api_key: string): Promise<Integracion> {
  return apiFetch<Integracion>("/api/integraciones/zernio", {
    method: "POST",
    body: JSON.stringify({ api_key }),
  })
}
