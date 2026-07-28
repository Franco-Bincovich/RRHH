/**
 * Estado de los filtros de vacaciones + carga de opciones (empresas, áreas, empleados) +
 * armado del array de FiltroCampo para <FiltersBar>. `onFiltroChange` se dispara en cada
 * cambio (la página lo usa para resetear la paginación a 1). El select de empleado solo
 * aparece con empresa definida (igual que áreas). El estado tiene opciones fijas
 * (planificada/tomada/cancelada) y se filtra server-side.
 */
import { useEffect, useState } from "react"

import { etiquetaArea } from "@/components/features/shared/filtros"
import type { FiltroCampo, RangoFechas } from "@/components/ui/FiltersBar"
import { fetchAreas } from "@/services/areas"
import type { VacacionesFiltros } from "@/services/vacaciones"
import { fetchEmpleadosSeleccionables } from "@/services/empleados"
import { fetchEmpresas } from "@/services/empresas"
import { fetchProyectos } from "@/services/proyectos"
import type { Proyecto } from "@/types/proyecto"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Area } from "@/types/area"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"

const ESTADO_OPCIONES = [
  { value: "planificada", label: "Planificada" },
  { value: "tomada", label: "Tomada" },
  { value: "cancelada", label: "Cancelada" },
]

export function useFiltrosVacaciones(onFiltroChange: () => void) {
  const [empresaActivaId, setEmpresaActivaId] = useState<string | null>(null)
  const [proyectoFiltro, setProyectoFiltro] = useState("")
  const [proyectos, setProyectos] = useState<Proyecto[]>([])
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [areaFiltro, setAreaFiltro] = useState("")
  const [areas, setAreas] = useState<Area[]>([])
  const [empleadoFiltro, setEmpleadoFiltro] = useState("")
  const [empleadosSel, setEmpleadosSel] = useState<EmpleadoSeleccionable[]>([])
  const [estadoFiltro, setEstadoFiltro] = useState("")
  const [rango, setRango] = useState<RangoFechas>({ desde: "", hasta: "" })

  useEffect(() => {
    const id = getEmpresaActivaId()
    setEmpresaActivaId(id)
    if (!id) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [])

  useEffect(() => {
    const empId = empresaActivaId || empresaFiltro || undefined
    fetchAreas(empId).then(setAreas).catch(() => setAreas([]))
    // El selector no necesita etiquetaProyecto: hoy no hay nombres de proyecto repetidos
    // entre empresas. Si algún día los hay, reusar el patrón de shared/filtros.ts.
    fetchProyectos({ empresaIdOverride: empId })
      .then((r) => setProyectos(r.items)).catch(() => setProyectos([]))
  }, [empresaActivaId, empresaFiltro])

  useEffect(() => {
    const empId = empresaActivaId || empresaFiltro
    if (!empId) { setEmpleadosSel([]); return }
    fetchEmpleadosSeleccionables(empId).then(setEmpleadosSel).catch(() => setEmpleadosSel([]))
  }, [empresaActivaId, empresaFiltro])


  const campos: FiltroCampo[] = [
    ...(!empresaActivaId && empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { setEmpresaFiltro(v); setAreaFiltro(""); setEmpleadoFiltro(""); onFiltroChange() },
      opciones: empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    ...(areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { setAreaFiltro(v); onFiltroChange() },
      opciones: areas.map((a) => ({ value: a.id, label: etiquetaArea(a, empresas, Boolean(empresaActivaId || empresaFiltro)) })) }] : []),
    ...(empleadosSel.length > 0 ? [{ tipo: "select" as const, label: "Empleado", value: empleadoFiltro, opcionTodos: "Todos los empleados",
      onChange: (v: string) => { setEmpleadoFiltro(v); onFiltroChange() },
      opciones: empleadosSel.map((e) => ({ value: e.id, label: `${e.apellido}, ${e.nombre}` })) }] : []),
    { tipo: "select" as const, label: "Estado", value: estadoFiltro, opcionTodos: "Todos los estados",
      onChange: (v: string) => { setEstadoFiltro(v); onFiltroChange() }, opciones: ESTADO_OPCIONES },
    { tipo: "daterange" as const, label: "Período",
      value: rango,
      onChange: (v: RangoFechas) => { setRango(v); onFiltroChange() } },
    ...(proyectos.length > 0 ? [{ tipo: "select" as const, label: "Proyecto", value: proyectoFiltro, opcionTodos: "Todos los proyectos",
      onChange: (v: string) => { setProyectoFiltro(v); onFiltroChange() },
      opciones: proyectos.map((p) => ({ value: p.id, label: p.nombre })) }] : []),
  ]

  // Un solo objeto de filtros: lo consumen el listado y el export, así que no pueden divergir.
  const filtros: VacacionesFiltros = {
    empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined,
    areaId: areaFiltro || undefined,
    empleadoId: empleadoFiltro || undefined,
    estado: estadoFiltro || undefined,
    fechaDesde: rango.desde || undefined,
    fechaHasta: rango.hasta || undefined,
    proyectoId: proyectoFiltro || undefined,
  }
  return { empresaActivaId, filtros, campos }
}
