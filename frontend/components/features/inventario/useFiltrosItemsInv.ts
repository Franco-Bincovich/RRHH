"use client"

/**
 * Estado de los filtros del catálogo de ítems (empresa, área y estado) y las opciones que los
 * llenan. Extraído de ItemsTab, que estaba en 152 contra un límite de 150.
 *
 * ⚠️ ACÁ DECÍA que esta pestaña "renderiza sus `<select>` a mano y cambiarlos sería tocar la UI",
 * y por eso no armaba `FiltroCampo`. **Eso dejó de ser cierto el 21/8/2026**: al migrar la
 * pantalla al patrón del bloque B, los tres `<select>` sueltos pasaron a `<FiltersBar panel>` y
 * los campos se arman en `_camposInventario.ts` —igual que en la pestaña hermana— para que
 * produzcan CHIPS y para que un test los pueda ejercitar sin DOM.
 *
 * ⚠️ Y LA CARGA DEL LISTADO SE FUE a `useListadoItemsInv`: con los campos adentro, este archivo
 * pasaba de 80 líneas, que es el límite de un hook. El corte es el mismo que ya tienen ausencias
 * y vacaciones — acá vive "qué está elegido", allá "qué llegó".
 *
 * `filtros` es UN solo objeto que consumen el listado Y el export: si se suma un filtro le
 * llega a los dos, que es la invariante del Bloque B.
 */
import { useEffect, useState } from "react"

import { construirCamposItems } from "@/components/features/inventario/_camposInventario"
import { fetchAreas } from "@/services/areas"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { ItemsFiltros } from "@/services/inventario"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"

export function useFiltrosItemsInv(onFiltroChange: () => void) {
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
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

  /** Al cambiar de empresa el área elegida deja de existir: se limpia, como en asignaciones. */
  const cambiarEmpresa = (v: string) => { setEmpresaFiltro(v); setAreaFiltro("") }

  const campos = construirCamposItems({
    empresaActivaId, empresas, empresaFiltro, cambiarEmpresa,
    estadoFiltro, setEstadoFiltro, areas, areaFiltro, setAreaFiltro, onFiltroChange,
  })

  const filtros: ItemsFiltros = {
    empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined,
    estado: estadoFiltro || undefined,
    areaId: areaFiltro || undefined,
  }

  return { empresaActivaId, campos, filtros }
}
