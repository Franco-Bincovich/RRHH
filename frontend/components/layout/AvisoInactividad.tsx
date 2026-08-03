"use client"

import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { AVISO_ANTES_MS, debeAvisar, minutosRestantes, msDesdeActividad } from "@/services/actividad"
import { fetchUsuarioVigente } from "@/services/auth"

/**
 * Avisa antes de que la sesión venza por inactividad (8 h sin un solo request al backend).
 *
 * ⚠️ Es UX, NO enforcement: el corte lo hace el middleware en cada request. Este banner solo
 * evita la versión desagradable de lo mismo —volver del almuerzo largo y encontrarse en el
 * login sin explicación, quizás con algo a medio cargar en pantalla.
 *
 * "Seguir conectado" no tiene magia: hace un request cualquiera (`/api/auth/me`), y ESE request
 * es el que sella `ultimo_acceso` del lado del servidor. Por eso el botón no necesita un
 * endpoint propio de "renovar sesión": renovar la sesión es, literalmente, usarla.
 */
const CADA_MINUTO = 60_000

export function AvisoInactividad() {
  const [visible, setVisible] = useState(false)
  const [minutos, setMinutos] = useState(0)

  useEffect(() => {
    // Se revisa por reloj y no por un timeout de 7h45: un timeout largo no sobrevive a que el
    // sistema suspenda, y volvería a dormir sin avisar nunca.
    const revisar = () => {
      const transcurrido = msDesdeActividad()
      setVisible(debeAvisar(transcurrido))
      setMinutos(minutosRestantes(transcurrido))
    }
    revisar()
    const id = setInterval(revisar, CADA_MINUTO)
    return () => clearInterval(id)
  }, [])

  if (!visible) return null

  return (
    <div
      role="status"
      className="fixed inset-x-0 bottom-0 z-50 flex flex-wrap items-center justify-center gap-3 border-t bg-card p-4 shadow-lg"
    >
      <p className="text-sm text-foreground">
        Tu sesión se va a cerrar por inactividad en {minutos} minuto{minutos === 1 ? "" : "s"}.
      </p>
      <Button
        size="sm"
        className="min-h-[2.75rem]"
        onClick={() => {
          // Best-effort: si falla, el interceptor ya se ocupa del 401 y del 403. Lo único que
          // se hace acá es sacar el banner para no dejarlo pegado con datos viejos.
          fetchUsuarioVigente().catch(() => {})
          setVisible(false)
        }}
      >
        Seguir conectado
      </Button>
    </div>
  )
}
