"use client"

import { useState } from "react"
import { Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import { clasificarPendientes } from "@/services/screening"
import type { ScreeningLoteResponse } from "@/types/screening"

/**
 * Botón "Clasificar CVs pendientes" de una vacante.
 *
 * 🔴 NO corre en la ingesta de mails: aquella ya tiene 240 s para leer la casilla y bajar
 * adjuntos, y sumarle N llamadas al modelo la cortaría a la mitad sin decir cuál mitad quedó.
 * Son dos botones a propósito.
 *
 * 🔴 El resultado NO es binario y por eso no se muestra como "listo": los cuatro números salen
 * enumerados. `sin_texto` no es un error (el CV no se pudo leer, va a revisión manual) y
 * `sin_procesar` es reintentable — volver a apretar toma solo los que quedaron, porque el
 * backend pide `clasificacion_ia IS NULL`. Un cartel de éxito escondería las tres cosas.
 */
export function ClasificarCvsButton({ vacanteId, onListo }: { vacanteId: string; onListo?: () => void }) {
  const [corriendo, setCorriendo] = useState(false)
  const [r, setR] = useState<ScreeningLoteResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const correr = async () => {
    setCorriendo(true)
    setError(null)
    try {
      setR(await clasificarPendientes(vacanteId))
      onListo?.()
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudieron clasificar los CVs.")
    } finally {
      setCorriendo(false)
    }
  }

  return (
    <div className="space-y-2">
      <Button variant="outline" size="sm" onClick={correr} disabled={corriendo}>
        <Sparkles className="size-4" />
        {corriendo ? "Clasificando..." : "Clasificar CVs pendientes"}
      </Button>

      {error && <p className="text-xs text-destructive">{error}</p>}

      {r && (
        <div className="space-y-1 rounded-lg border bg-muted/40 p-3 text-xs text-muted-foreground">
          <p><strong className="text-foreground">{r.clasificados}</strong> CV{r.clasificados !== 1 ? "s" : ""} clasificado{r.clasificados !== 1 ? "s" : ""} en {r.segundos.toFixed(1)} s.</p>
          {r.sin_texto > 0 && (
            <p>{r.sin_texto} sin texto legible: no se clasificaron y quedan para revisar a mano.</p>
          )}
          {r.errores > 0 && (
            <p className="text-destructive">{r.errores} con error: quedaron sin clasificar, se pueden reintentar.</p>
          )}
          {r.sin_procesar > 0 && (
            <p>
              Quedaron <strong className="text-foreground">{r.sin_procesar}</strong> sin procesar
              {r.tope_alcanzado ? " (tope por corrida)" : " (se acabó el tiempo de la corrida)"}.
              Volvé a apretar el botón para seguir con esos.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
