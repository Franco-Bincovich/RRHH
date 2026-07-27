/**
 * Estado de los filtros de empleados + carga de opciones (empresas, áreas) + armado del
 * array de FiltroCampo para <FiltersBar>. El search se DEBOUNCEA acá: `debouncedSearch` es
 * lo que la página usa para el fetch, y el reset de página (via `onFiltroChange`) se dispara
 * junto con el commit del debounce — mismo tick, un solo fetch, sin perder el reset.
 * Los demás filtros (empresa/área/estado) resetean página en su onChange inmediato.
 */
import { useEffect, useState } from "react"

import type { FiltroCampo } from "@/components/ui/FiltersBar"
import { fetchAreas } from "@/services/areas"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"

const LIDER_OPCIONES = [
  { value: "si", label: "Solo líderes" },
  { value: "no", label: "Solo no líderes" },
]

const ESTADO_OPCIONES = [
  { value: "activo", label: "Activo" },
  { value: "baja", label: "Baja" },
  { value: "licencia", label: "Licencia" },
]

export function useFiltrosEmpleados(onFiltroChange: () => void) {
  const [empresaActivaId, setEmpresaActivaId] = useState<string | null>(null)
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [areaFiltro, setAreaFiltro] = useState("")
  const [areas, setAreas] = useState<Area[]>([])
  const [estadoFiltro, setEstadoFiltro] = useState("")
  // "" = sin filtro · "si"/"no" → true/false. Se guarda como texto porque el control es un
  // select; la traducción a booleano se hace una sola vez, abajo, al armar `esLider`.
  const [liderFiltro, setLiderFiltro] = useState("")
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")

  useEffect(() => {
    const id = getEmpresaActivaId()
    setEmpresaActivaId(id)
    if (!id) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [])

  useEffect(() => {
    const empId = empresaActivaId || empresaFiltro || undefined
    fetchAreas(empId).then(setAreas).catch(() => setAreas([]))
  }, [empresaActivaId, empresaFiltro])

  // Debounce del search: commitea el valor y resetea la página en el mismo tick (un solo fetch).
  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); onFiltroChange() }, 350)
    return () => clearTimeout(t)
  }, [search])  // eslint-disable-line react-hooks/exhaustive-deps

  function areaLabel(area: Area): string {
    if (!empresaActivaId && !empresaFiltro) {
      const emp = empresas.find((e) => e.id === area.empresa_id)
      return emp ? `${area.nombre} — ${emp.nombre}` : area.nombre
    }
    return area.nombre
  }

  const campos: FiltroCampo[] = [
    { tipo: "search" as const, label: "Buscar", value: search, placeholder: "Buscar por nombre...", onChange: setSearch },
    ...(!empresaActivaId && empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { setEmpresaFiltro(v); setAreaFiltro(""); onFiltroChange() },
      opciones: empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    ...(areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { setAreaFiltro(v); onFiltroChange() },
      opciones: areas.map((a) => ({ value: a.id, label: areaLabel(a) })) }] : []),
    { tipo: "select" as const, label: "Estado", value: estadoFiltro, opcionTodos: "Todos los estados",
      onChange: (v: string) => { setEstadoFiltro(v); onFiltroChange() }, opciones: ESTADO_OPCIONES },
    { tipo: "select" as const, label: "Liderazgo", value: liderFiltro, opcionTodos: "Todos",
      onChange: (v: string) => { setLiderFiltro(v); onFiltroChange() }, opciones: LIDER_OPCIONES },
  ]

  const empresaOverride = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined
  // `false` es un filtro válido (solo no-líderes), así que no se puede colapsar con `|| undefined`.
  const esLider = liderFiltro === "" ? undefined : liderFiltro === "si"
  return { empresaActivaId, empresaOverride, areaFiltro, estadoFiltro, esLider, debouncedSearch, campos }
}
