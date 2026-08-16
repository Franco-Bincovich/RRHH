"use client"

import { useCallback, useEffect, useState } from "react"

import { fetchAreasPagina } from "@/services/areas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Area } from "@/types/area"

export const PAGE_SIZE = 20

/**
 * La LISTA de la pantalla de áreas: su página, su total y la búsqueda. El ABM (modal, edición,
 * borrado) vive en `useAreasAcciones` — son dos ciclos de vida distintos y juntos pasaban de 80.
 *
 * 🔴 EL BUSCADOR ES SERVER-SIDE DESDE EL 15/8/2026, Y ESE CAMBIO ES EL MOTIVO DE LA SESIÓN.
 * Antes filtraba sobre el array ya traído (`areas.filter(...)`), lo que tenía dos consecuencias:
 *
 *   · **con paginación se rompe en silencio**: buscás un área que existe pero está en la
 *     página 3, el filtro nunca ve esa fila y la pantalla dice que no hay resultados. No hay
 *     error, y el estado vacío es indistinguible de "esa área no existe";
 *   · **el export no veía el filtro** (invariante 1 del bloque B): buscabas "Sistemas", la
 *     pantalla mostraba 3 filas y el archivo salía con las 58 de la empresa.
 *
 * Ahora `search` viaja al backend en el MISMO objeto que consume el export, así que las dos
 * superficies no pueden divergir.
 *
 * ⚠️ NO expone `filtradas`: no existe más. Si aparece un `.filter()` sobre `areas` en esta
 * pantalla, es la regresión.
 */
export function useAreas() {
  const [areas, setAreas] = useState<Area[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [search, setSearchRaw] = useState("")
  const [buscado, setBuscado] = useState("")

  // 🔴 Escribir vuelve a la página 1 (invariante 4 del bloque B): buscar parado en la 3 pediría
  // una página que el resultado nuevo no tiene y la tabla saldría vacía sobre un término que sí
  // tiene áreas — indistinguible de "no encontré nada".
  const setSearch = (v: string) => { setPage(1); setSearchRaw(v) }

  // El término viaja al servidor recién a los 300 ms: sin esto, cada tecla es un request.
  useEffect(() => {
    const t = setTimeout(() => setBuscado(search.trim()), 300)
    return () => clearTimeout(t)
  }, [search])

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchAreasPagina(
        getEmpresaActivaId() ?? undefined, buscado || undefined, page, PAGE_SIZE,
      )
      setAreas(data.items)
      setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [buscado, page])

  useEffect(() => { void load() }, [load])

  return { areas, total, page, setPage, loading, error, search, setSearch, buscado, load }
}
