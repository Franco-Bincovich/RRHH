"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import {
  conActivoParcheado, conEntrevista,
} from "@/components/features/offboarding/_offboardingEstado"
import { fetchOffboardings, marcarActivoDevuelto } from "@/services/offboarding"
import type { ActivoResponse, OffboardingInstancia } from "@/types/offboarding"

/**
 * El estado del listado de offboardings: la carga, el toggle optimista de un activo con su
 * revert, y las mutaciones locales que las tarjetas disparan.
 *
 * Extraído de `app/(dashboard)/offboarding/page.tsx` (311/150) al sumarle la efectivización de
 * la baja. El corte es por CAPA y no por largo: un `page.tsx` no tiene por qué contener un
 * update optimista con revert, y el próximo cambio de la tarjeta no debería obligar a leer el
 * fetch. Las transformaciones puras de la lista viven en `_offboardingEstado.ts`.
 *
 * 🔴 EL TOGGLE ES OPTIMISTA, y eso es lo que justifica el revert. La casilla se pinta antes de
 * que el backend conteste porque devolver activos son varios clics seguidos y esperar el
 * round-trip en cada uno la vuelve inusable. El precio es tener que deshacer: el revert restaura
 * EL ACTIVO ORIGINAL que llegó por parámetro, no un "estado anterior" recalculado — entre el
 * clic y el error pudo haber cambiado otra cosa de la misma instancia.
 */
export function useOffboardings() {
  const [offboardings, setOffboardings] = useState<OffboardingInstancia[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState<string | null>(null)

  useEffect(() => {
    fetchOffboardings()
      .then(setOffboardings)
      .catch(() => setError("No se pudieron cargar los offboardings"))
      .finally(() => setLoading(false))
  }, [])

  const toggleActivo = useCallback(async (instanciaId: string, activo: ActivoResponse) => {
    const devuelto = !activo.devuelto
    setSaving(`${instanciaId}-${activo.id}`)
    setOffboardings((prev) => conActivoParcheado(prev, instanciaId, activo.id, (a) => ({
      ...a, devuelto, estado: devuelto ? "devuelto" : "pendiente",
    })))
    try {
      await marcarActivoDevuelto(instanciaId, activo.id, devuelto)
    } catch {
      toast.error("No se pudo actualizar el activo. Intentá de nuevo.")
      setOffboardings((prev) => conActivoParcheado(prev, instanciaId, activo.id, () => activo))
    } finally {
      setSaving(null)
    }
  }, [])

  const marcarEntrevista = useCallback((id: string, realizada: boolean, notas: string | null) => {
    setOffboardings((prev) => conEntrevista(prev, id, realizada, notas))
  }, [])

  /**
   * Saca la instancia de la lista después de efectivizar su baja. NO se recarga el listado: el
   * endpoint devuelve solo los procesos abiertos, así que el recién cerrado ya no vendría — y un
   * refetch le agregaría un parpadeo a toda la pantalla para quitar una tarjeta que sabemos cuál es.
   */
  const quitar = useCallback((id: string) => {
    setOffboardings((prev) => prev.filter((o) => o.id !== id))
  }, [])

  return { offboardings, loading, error, saving, toggleActivo, marcarEntrevista, quitar }
}
