/**
 * Estado de los filtros de proyectos + armado del array de FiltroCampo para <FiltersBar>.
 * Sigue el molde de components/features/shared/filtros.ts: un solo objeto de filtros que
 * consumen el listado y, cuando exista, el export.
 *
 * `onFiltroChange` se dispara en cada cambio; la página lo cablea a resetear la paginación
 * (hoy este listado no pagina, pero el contrato queda igual que en el resto de los módulos).
 */
import { useEffect, useState } from "react"

import { etiquetaArea } from "@/components/features/shared/filtros"
import type { FiltroCampo } from "@/components/ui/FiltersBar"
import { fetchAreas } from "@/services/areas"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"
import type { ProyectosFiltros } from "@/services/proyectos"
import type { ProyectoEstado } from "@/types/proyecto"

const ESTADO_OPCIONES: { value: ProyectoEstado; label: string }[] = [
  { value: "activo", label: "Activo" },
  { value: "pausado", label: "Pausado" },
  { value: "cerrado", label: "Cerrado" },
  { value: "cancelado", label: "Cancelado" },
]

export function useFiltrosProyectos(onFiltroChange: () => void) {
  const [estadoFiltro, setEstadoFiltro] = useState("")
  const [areaFiltro, setAreaFiltro] = useState("")
  const [areas, setAreas] = useState<Area[]>([])
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [empresaFiltro, setEmpresaFiltro] = useState("")

  const empresaId = empresaActivaId || empresaFiltro

  useEffect(() => {
    if (!empresaActivaId) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [empresaActivaId])

  useEffect(() => {
    fetchAreas(empresaId || undefined).then(setAreas).catch(() => setAreas([]))
  }, [empresaId])

  const campos: FiltroCampo[] = [
    ...(!empresaActivaId && empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { setEmpresaFiltro(v); setAreaFiltro(""); onFiltroChange() },
      opciones: empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    { tipo: "select", label: "Estado", value: estadoFiltro, opcionTodos: "Todos los estados",
      onChange: (v: string) => { setEstadoFiltro(v); onFiltroChange() }, opciones: ESTADO_OPCIONES },
    ...(areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { setAreaFiltro(v); onFiltroChange() },
      opciones: areas.map((a) => ({ value: a.id, label: etiquetaArea(a, empresas, Boolean(empresaId)) })) }] : []),
  ]

  const filtros: ProyectosFiltros = {
    empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined,
    estado: estadoFiltro || undefined,
    areaId: areaFiltro || undefined,
  }
  return { filtros, campos }
}
