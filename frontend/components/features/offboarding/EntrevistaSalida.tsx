"use client"

import { useState } from "react"
import { MessageSquare } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { registrarEntrevista } from "@/services/offboarding"
import { ApiError } from "@/services/api"
import type { OffboardingInstancia } from "@/types/offboarding"

/**
 * Entrevista de salida de un offboarding: si se realizó y sus notas.
 *
 * Vive en su propio componente y no dentro de offboarding/page.tsx porque esa página ya está
 * en 292 líneas contra un límite de 150 — meterle el bloque acá adentro la empujaría todavía
 * más lejos. La página solo la monta.
 *
 * El estado es local y optimista sobre el guardado: la página no vuelve a pedir la lista, así
 * que `onGuardado` le avisa qué quedó persistido para que su copia no muestre lo viejo.
 */
export function EntrevistaSalida({
  instancia,
  canWrite,
  onGuardado,
}: {
  instancia: OffboardingInstancia
  canWrite: boolean
  onGuardado: (id: string, realizada: boolean, notas: string | null) => void
}) {
  const [realizada, setRealizada] = useState(instancia.entrevista_salida)
  const [notas, setNotas] = useState(instancia.notas_entrevista ?? "")
  const [guardando, setGuardando] = useState(false)

  const sinCambios =
    realizada === instancia.entrevista_salida && notas === (instancia.notas_entrevista ?? "")

  async function guardar() {
    setGuardando(true)
    try {
      const limpias = notas.trim() || null
      await registrarEntrevista(instancia.id, realizada, limpias)
      onGuardado(instancia.id, realizada, limpias)
      toast.success("Entrevista de salida registrada")
    } catch (e) {
      // El backend explica el motivo (p. ej. el proceso ya no está); el genérico queda para
      // lo que no viene de la API, donde reintentar sí es el consejo correcto.
      toast.error(e instanceof ApiError ? e.message : "No se pudo guardar. Intentá de nuevo.")
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="mt-4 border-t pt-3">
      <div className="flex items-center gap-2">
        <MessageSquare className="size-4 text-muted-foreground" />
        <h3 className="text-sm font-medium text-foreground">Entrevista de salida</h3>
      </div>

      <label className="mt-2 flex items-center gap-2 text-sm text-foreground">
        <input
          type="checkbox"
          checked={realizada}
          disabled={!canWrite || guardando}
          onChange={(e) => setRealizada(e.target.checked)}
          className="size-4 rounded border-input"
        />
        Se realizó la entrevista
      </label>

      <Textarea
        value={notas}
        disabled={!canWrite || guardando}
        onChange={(e) => setNotas(e.target.value)}
        placeholder="Notas de la entrevista (opcional)"
        rows={3}
        className="mt-2 text-sm"
        aria-label="Notas de la entrevista de salida"
      />

      {canWrite && (
        <Button
          size="sm"
          className="mt-2 min-h-11"
          disabled={guardando || sinCambios}
          onClick={guardar}
        >
          {guardando ? "Guardando..." : "Guardar entrevista"}
        </Button>
      )}
    </div>
  )
}
