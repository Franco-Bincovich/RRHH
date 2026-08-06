"use client"

/**
 * Estado de los filtros del catálogo de ítems (empresa, área y estado) + la carga del listado.
 * Extraído de ItemsTab, que estaba en 152 contra un límite de 150.
 *
 * Molde: useFiltrosAsignacionesInv.ts. Difiere en dos cosas, las dos a propósito: acá NO se
 * arma el array de `FiltroCampo` para <FiltersBar> —esta pestaña renderiza sus `<select>` a
 * mano y cambiarlos sería tocar la UI— y sí se lleva el listado, para que ItemsTab quede como
 * orquestador.
 *
 * `filtros` es UN solo objeto que consumen el listado Y el export: si se suma un filtro le
 * llega a los dos, que es la invariante del Bloque B.
 */
import { useCallback, useEffect, useState } from "react"

import { etiquetaArea } from "@/components/features/shared/filtros"
import { fetchAreas } from "@/services/areas"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { fetchItems, type ItemsFiltros } from "@/services/inventario"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"
import type { InventarioItem } from "@/types/inventario"

export function useFiltrosItemsInv() {
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [items, setItems] = useState<InventarioItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [estadoFiltro, setEstadoFiltro] = useState("")
  const [areaFiltro, setAreaFiltro] = useState("")
  const [areas, setAreas] = useState<Area[]>([])

  const empresaId = empresaActivaId || empresaFiltro

  useEffect(() => {
    if (!empresaActivaId)
      fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [empresaActivaId])

  // Mismo criterio que useFiltrosAsignacionesInv: las áreas son POR empresa, así que se
  // recargan cuando cambia la empresa mirada.
  useEffect(() => {
    fetchAreas(empresaId || undefined).then(setAreas).catch(() => setAreas([]))
  }, [empresaId])

  const load = useCallback(async () => {
    setLoading(true); setError(false)
    try {
      const override = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined
      const data = await fetchItems({ empresaIdOverride: override, estado: estadoFiltro || undefined, areaId: areaFiltro || undefined })
      setItems(data.items)
    } catch { setError(true) }
    finally { setLoading(false) }
  }, [empresaActivaId, empresaFiltro, estadoFiltro, areaFiltro])

  useEffect(() => { load() }, [load])

  const filtros: ItemsFiltros = {
    empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined,
    estado: estadoFiltro || undefined,
    areaId: areaFiltro || undefined,
  }

  /** Al cambiar de empresa el área elegida deja de existir: se limpia, como en asignaciones. */
  const cambiarEmpresa = (v: string) => { setEmpresaFiltro(v); setAreaFiltro("") }

  const opcionesArea = areas.map((a) => ({ value: a.id, label: etiquetaArea(a, empresas, Boolean(empresaId)) }))

  return {
    empresaActivaId, empresas, empresaFiltro, cambiarEmpresa,
    estadoFiltro, setEstadoFiltro, areaFiltro, setAreaFiltro, opcionesArea,
    items, loading, error, load, filtros,
  }
}
