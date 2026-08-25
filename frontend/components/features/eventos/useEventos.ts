"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { cargarEventos } from "@/components/features/eventos/cargarEventos"
import { setEventoResuelta } from "@/services/eventos"
import type { Evento } from "@/types/evento"

export const PAGE_SIZE_INICIAL = 20

/**
 * El listado de la agenda: página, filtro de resueltos y el toggle de cada fila.
 *
 * Salió de `eventos/page.tsx`, que llegó a 164 líneas contra el límite de 150. La página se
 * queda con lo que abre y cierra diálogos —modal de alta/edición y confirmación de baja—, que es
 * estado de PANTALLA; acá vive el estado de DATOS.
 *
 * ⚠️ `alternarResueltas` YA NO EXISTE: era el toggle de un botón, y al migrar la pantalla al
 * patrón del bloque B el filtro pasó a ser un `<select>` dentro del panel para que produzca CHIP.
 * Lo que sí se conserva —y es lo que importa— es que el setter resetea la página; ver el 🔴 del
 * `return`.
 */
export function useEventos() {
  const [eventos, setEventos] = useState<Evento[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  /*
   * 🔴 EL FILTRO SE GUARDA COMO TEXTO ("" | "todos") Y NO COMO BOOLEAN, y no es un capricho: los
   * chips del patrón se derivan de un `FiltroCampo`, y el único control que puede expresar esto
   * es un `select`, que trabaja con strings. La traducción a `incluir_resueltas: boolean` —lo
   * único que el backend entiende— se hace UNA vez, abajo, al armar el pedido.
   */
  const [resueltosFiltro, setResueltosFiltro] = useState("")
  const incluirResueltas = resueltosFiltro === "todos"

  const load = useCallback(
    () => cargarEventos({ incluirResueltas }, page, pageSize,
                        { setEventos, setTotal, setLoading, setError }),
    [incluirResueltas, page, pageSize],
  )
  useEffect(() => { void load() }, [load])

  async function cambiarResuelta(evento: Evento, resuelta: boolean) {
    try {
      await setEventoResuelta(evento.id, resuelta)
      void load()
    } catch {
      toast.error("No se pudo cambiar el estado del recordatorio. Intentá de nuevo.")
    }
  }

  return {
    eventos, total, page, pageSize, setPageSize, setPage, loading, error, load,
    resueltosFiltro,
    // 🔴 El setter que la pantalla le pasa al filtro VUELVE A LA PÁGINA 1 (invariante 4 del
    // bloque B). Vive acá y no en la página justamente por eso: mientras el filtro y el `setPage`
    // estén en el mismo lugar, no hay forma de mover uno y olvidarse del otro. Sin eso, alguien
    // parado en la página 4 de los pendientes que pide ver los resueltos puede caer fuera del
    // nuevo total y ver una tabla vacía con el endpoint respondiendo 200.
    setResueltosFiltro: (v: string) => { setResueltosFiltro(v); setPage(1) },
    cambiarResuelta,
  }
}
