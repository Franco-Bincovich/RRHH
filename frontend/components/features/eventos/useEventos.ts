"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { cargarEventos } from "@/components/features/eventos/cargarEventos"
import { setEventoResuelta } from "@/services/eventos"
import type { Evento } from "@/types/evento"

export const PAGE_SIZE = 20

/**
 * El listado de la agenda: página, filtro de resueltos y el toggle de cada fila.
 *
 * Salió de `eventos/page.tsx`, que llegó a 164 líneas contra el límite de 150. La página se
 * queda con lo que abre y cierra diálogos —modal de alta/edición y confirmación de baja—, que es
 * estado de PANTALLA; acá vive el estado de DATOS.
 *
 * 🔴 `alternarResueltas` VUELVE A LA PÁGINA 1, y es la regla del bloque B ("`page` se resetea al
 * cambiar cualquier filtro"). Vive acá y no en la página justamente por eso: mientras el toggle y
 * el `setPage` estén en el mismo lugar, no hay forma de mover uno y olvidarse del otro. Sin eso,
 * alguien parado en la página 4 de los pendientes que destilda el filtro puede caer fuera del
 * nuevo total y ver una tabla vacía con el endpoint respondiendo 200.
 */
export function useEventos() {
  const [eventos, setEventos] = useState<Evento[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [incluirResueltas, setIncluirResueltas] = useState(false)

  const load = useCallback(
    () => cargarEventos({ incluirResueltas }, page, PAGE_SIZE,
                        { setEventos, setTotal, setLoading, setError }),
    [incluirResueltas, page],
  )
  useEffect(() => { void load() }, [load])

  async function cambiarResuelta(evento: Evento, resuelta: boolean) {
    try {
      await setEventoResuelta(evento.id, resuelta)
      void load()
    } catch {
      toast.error("No se pudo cambiar el estado del evento. Intentá de nuevo.")
    }
  }

  return {
    eventos, total, page, setPage, loading, error, load,
    incluirResueltas,
    alternarResueltas: () => { setIncluirResueltas((v) => !v); setPage(1) },
    cambiarResuelta,
  }
}
