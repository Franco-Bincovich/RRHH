"use client"

import { useEffect } from "react"
import { useSearchParams } from "next/navigation"

/**
 * Cierra el popup de OAuth avisándole a la ventana que lo abrió.
 *
 * Google redirige el navegador de vuelta a /configuracion?oauth=… DENTRO del popup; este
 * componente corre ahí, le manda el resultado al opener por postMessage y se cierra.
 *
 * Vive en un archivo aparte porque usa useSearchParams: eso obliga a envolverlo en un
 * <Suspense>, y sin separarlo el boundary se comería la página entera.
 */
export function OAuthPopupHandler() {
  const searchParams = useSearchParams()
  const oauth = searchParams.get("oauth")

  useEffect(() => {
    if (!oauth) return
    try {
      if (window.opener) {
        window.opener.postMessage(
          { type: "oauth_complete", provider: oauth },
          window.location.origin,
        )
        window.close()
      }
    } catch {
      // opener podría estar bloqueado; no hace nada
    }
  }, [oauth])

  return null
}
