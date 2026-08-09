"use client"

import { useState } from "react"
import { PencilLine } from "lucide-react"

import { Button } from "@/components/ui/button"
import { corregirClasificacion } from "@/services/screening"
import type { ClasificacionIA } from "@/types/candidato"

const OPCIONES: { value: ClasificacionIA; label: string }[] = [
  { value: "relevante", label: "Relevante" },
  { value: "dudoso", label: "Dudoso" },
  { value: "no_relevante", label: "No relevante" },
]

interface Props {
  candidatoId: string
  actual: ClasificacionIA | null
  motivoActual: string | null
  onCorregido?: () => void
}

/**
 * El control que cierra la promesa del módulo: "un humano revisa siempre".
 *
 * 🔴 Hasta que existió esto, el humano podía MIRAR y no corregir. El único write de
 * `clasificacion_ia` era el clasificador, y el botón de la corrida solo toma los que están sin
 * clasificar, así que un `no_relevante` equivocado era permanente.
 *
 * 🔴 El motivo es OBLIGATORIO y el botón está deshabilitado sin él. No es rigor por rigor: la
 * clasificación que se pisa ya venía con su motivo, y cambiar la etiqueta sin escribir por qué
 * dejaría la ficha diciendo "Relevante" con la explicación del "No relevante" anterior. Además
 * es el dato que después se lee para saber en qué se equivoca el filtro.
 *
 * ⚠️ No se puede volver a "sin clasificar": las tres categorías son el conjunto cerrado. Un
 * cuarto estado haría indistinguible al candidato que alguien vació del que nunca se clasificó.
 */
export function CorregirClasificacion({ candidatoId, actual, motivoActual, onCorregido }: Props) {
  const [abierto, setAbierto] = useState(false)
  const [valor, setValor] = useState<ClasificacionIA>(actual ?? "dudoso")
  const [motivo, setMotivo] = useState(motivoActual ?? "")
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const guardar = async () => {
    setGuardando(true)
    setError(null)
    try {
      await corregirClasificacion(candidatoId, valor, motivo.trim())
      setAbierto(false)
      onCorregido?.()
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar la corrección.")
    } finally {
      setGuardando(false)
    }
  }

  if (!abierto) {
    return (
      <Button variant="ghost" size="sm" onClick={() => setAbierto(true)}>
        <PencilLine className="size-3.5" />
        {actual ? "Corregir clasificación" : "Clasificar a mano"}
      </Button>
    )
  }

  return (
    <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
      <select
        aria-label="Clasificación"
        className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
        value={valor}
        onChange={(e) => setValor(e.target.value as ClasificacionIA)}
      >
        {OPCIONES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>

      <textarea
        aria-label="Motivo"
        rows={2}
        maxLength={400}
        placeholder="Por qué. En términos de lo que el CV dice."
        className="w-full rounded-md border border-input bg-background p-2 text-sm"
        value={motivo}
        onChange={(e) => setMotivo(e.target.value)}
      />

      {error && <p className="text-xs text-destructive">{error}</p>}

      <div className="flex gap-2">
        <Button size="sm" onClick={guardar} disabled={guardando || !motivo.trim()}>
          {guardando ? "Guardando..." : "Guardar"}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setAbierto(false)} disabled={guardando}>
          Cancelar
        </Button>
      </div>
    </div>
  )
}
