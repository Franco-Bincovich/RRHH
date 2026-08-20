/**
 * Estado de los filtros de asignaciones de inventario + carga de opciones + armado del array
 * de FiltroCampo para <FiltersBar>. Sigue el molde de components/features/shared/filtros.ts:
 * un solo objeto de filtros que consumen el listado Y el export, así no pueden divergir.
 *
 * `onFiltroChange` se dispara en cada cambio; la página lo cablea a resetear la paginación
 * (este listado no pagina hoy, pero el contrato queda igual que en el resto de los módulos).
 */
import { useEffect, useState } from "react"

import { etiquetaArea } from "@/components/features/shared/filtros"
import type { FiltroCampo } from "@/components/ui/FiltersBar"
import { fetchAreas } from "@/services/areas"
import type { Area } from "@/types/area"
import { fetchEmpleadosSeleccionables } from "@/services/empleados"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { AsignacionesInventarioFiltros } from "@/services/inventario"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"

export function useFiltrosAsignacionesInv(onFiltroChange: () => void) {
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empleadoFiltro, setEmpleadoFiltro] = useState("")
  const [empleados, setEmpleados] = useState<EmpleadoSeleccionable[]>([])
  const [areaFiltro, setAreaFiltro] = useState("")
  const [areas, setAreas] = useState<Area[]>([])

  const empresaId = empresaActivaId || empresaFiltro

  useEffect(() => {
    if (!empresaActivaId) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [empresaActivaId])

  useEffect(() => {
    fetchAreas(empresaId || undefined).then(setAreas).catch(() => setAreas([]))
  }, [empresaId])

  useEffect(() => {
    // El selector de empleados exige empresa concreta (mismo criterio que el resto del repo).
    if (!empresaId) { setEmpleados([]); return }
    fetchEmpleadosSeleccionables(empresaId).then(setEmpleados).catch(() => setEmpleados([]))
  }, [empresaId])

  const campos: FiltroCampo[] = [
    ...(!empresaActivaId && empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { setEmpresaFiltro(v); setEmpleadoFiltro(""); setAreaFiltro(""); onFiltroChange() },
      opciones: empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    ...(areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { setAreaFiltro(v); onFiltroChange() },
      opciones: areas.map((a) => ({ value: a.id, label: etiquetaArea(a, empresas, Boolean(empresaId)) })) }] : []),
    ...(empleados.length > 0 ? [{ tipo: "select" as const, label: "Colaborador", value: empleadoFiltro, opcionTodos: "Todos los colaboradores",
      onChange: (v: string) => { setEmpleadoFiltro(v); onFiltroChange() },
      opciones: empleados.map((e) => ({ value: e.id, label: `${e.apellido}, ${e.nombre}` })) }] : []),
  ]

  const filtros: AsignacionesInventarioFiltros = {
    empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined,
    empleadoId: empleadoFiltro || undefined,
    areaId: areaFiltro || undefined,
  }
  return { empresaActivaId, filtros, campos }
}
