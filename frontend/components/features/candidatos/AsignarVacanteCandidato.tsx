"use client"

import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { Select } from "@/components/ui/select"
import { asignarVacanteACandidato } from "@/services/candidatos"
import { fetchVacantes } from "@/services/vacantes"
import type { Vacante } from "@/types/vacantes"

/**
 * Le asigna una búsqueda a un candidato que quedó huérfano.
 *
 * 🔴 Solo se muestra para candidatos con `vacante_id === null`. Un candidato con búsqueda BORRADA
 * (que tiene `busqueda_congelada` y `busqueda_activa === false`) también es huérfano y también
 * puede reasignarse — de ahí que la condición sea sobre `vacante_id` y no sobre `busqueda_activa`,
 * que son cosas distintas y se confunden fácil.
 *
 * ⚠️ El backend rechaza asignar a una vacante de OTRA empresa (la de referencia es la del
 * candidato, no la del selector de la barra). El mensaje del error se muestra tal cual.
 */
interface Props {
  candidatoId: string
  onAsignada?: () => void
}

export function AsignarVacanteCandidato({ candidatoId, onAsignada }: Props) {
  const [vacantes, setVacantes] = useState<Vacante[]>([])
  const [elegida, setElegida] = useState("")
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // ⚠️ Es un SELECTOR, no un listado: necesita todas las vacantes elegibles, así que pide
    // el tope del endpoint (100, el `le` del router). Si alguna vez hay más de 100 abiertas,
    // esto pasa a ser un combobox con búsqueda server-side, no un `page_size` más grande.
    fetchVacantes(undefined, undefined, 1, 100).then((r) => setVacantes(r.items)).catch(() => setVacantes([]))
  }, [])

  async function asignar() {
    if (!elegida) return
    setGuardando(true)
    setError(null)
    try {
      await asignarVacanteACandidato(candidatoId, elegida)
      onAsignada?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo asignar la búsqueda.")
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="space-y-2">
      <Select
        aria-label="Asignar a una búsqueda"
        value={elegida}
        onChange={(e) => setElegida(e.target.value)}
      >
        <option value="">Elegí una búsqueda…</option>
        {vacantes.map((v) => (
          <option key={v.id} value={v.id}>{v.codigo} · {v.titulo}</option>
        ))}
      </Select>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button className="min-h-10 w-full" disabled={!elegida || guardando} onClick={asignar}>
        {guardando ? "Asignando…" : "Asignar a esta búsqueda"}
      </Button>
    </div>
  )
}
