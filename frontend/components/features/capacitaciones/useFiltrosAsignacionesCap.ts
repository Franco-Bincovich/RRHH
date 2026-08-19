/**
 * Estado de los filtros de asignaciones de capacitación + carga de opciones + armado del array
 * de FiltroCampo para <FiltersBar>. Sigue el molde de components/features/shared/filtros.ts:
 * un solo objeto de filtros que consumen el listado Y el export, así no pueden divergir.
 *
 * `onFiltroChange` se dispara en cada cambio; la página lo cablea a resetear la paginación.
 *
 * Los selects de área, empleado y capacitación solo aparecen cuando hay opciones que ofrecer:
 * un filtro con la lista vacía no acota nada y solo ocupa lugar.
 */
import { useEffect, useState } from "react"

import type { FiltroCampo } from "@/components/ui/FiltersBar"
import { fetchAreas } from "@/services/areas"
import type { AsignacionesCapacitacionFiltros } from "@/services/capacitaciones"
import { fetchCapacitaciones } from "@/services/capacitaciones"
import { fetchEmpleadosSeleccionables } from "@/services/empleados"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Area } from "@/types/area"
import type { Capacitacion } from "@/types/capacitacion"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"

const ESTADO_OPCIONES = [
  { value: "pendiente", label: "Pendiente" },
  { value: "en_curso", label: "En curso" },
  { value: "completado", label: "Completado" },
]

export function useFiltrosAsignacionesCap(onFiltroChange: () => void) {
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [areaFiltro, setAreaFiltro] = useState("")
  const [areas, setAreas] = useState<Area[]>([])
  const [empleadoFiltro, setEmpleadoFiltro] = useState("")
  const [empleados, setEmpleados] = useState<EmpleadoSeleccionable[]>([])
  const [capacitacionFiltro, setCapacitacionFiltro] = useState("")
  const [capacitaciones, setCapacitaciones] = useState<Capacitacion[]>([])
  const [estadoFiltro, setEstadoFiltro] = useState("")

  const empresaId = empresaActivaId || empresaFiltro

  useEffect(() => {
    if (!empresaActivaId) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [empresaActivaId])

  useEffect(() => {
    fetchAreas(empresaId || undefined).then(setAreas).catch(() => setAreas([]))
  }, [empresaId])

  useEffect(() => {
    // El selector de empleados exige empresa concreta (igual que en vacaciones/ausencias).
    if (!empresaId) { setEmpleados([]); return }
    fetchEmpleadosSeleccionables(empresaId).then(setEmpleados).catch(() => setEmpleados([]))
  }, [empresaId])

  useEffect(() => {
    fetchCapacitaciones(empresaId || undefined, true)
      .then((r) => setCapacitaciones(r.items)).catch(() => setCapacitaciones([]))
  }, [empresaId])

  const campos: FiltroCampo[] = [
    ...(!empresaActivaId && empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { setEmpresaFiltro(v); setAreaFiltro(""); setEmpleadoFiltro(""); setCapacitacionFiltro(""); onFiltroChange() },
      opciones: empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    ...(areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { setAreaFiltro(v); onFiltroChange() },
      opciones: areas.map((a) => ({ value: a.id, label: a.nombre })) }] : []),
    ...(empleados.length > 0 ? [{ tipo: "select" as const, label: "Empleado", value: empleadoFiltro, opcionTodos: "Todos los empleados",
      onChange: (v: string) => { setEmpleadoFiltro(v); onFiltroChange() },
      opciones: empleados.map((e) => ({ value: e.id, label: `${e.apellido}, ${e.nombre}` })) }] : []),
    ...(capacitaciones.length > 0 ? [{ tipo: "select" as const, label: "Formación", value: capacitacionFiltro, opcionTodos: "Todas las formaciones",
      onChange: (v: string) => { setCapacitacionFiltro(v); onFiltroChange() },
      opciones: capacitaciones.map((c) => ({ value: c.id, label: c.nombre })) }] : []),
    { tipo: "select" as const, label: "Estado", value: estadoFiltro, opcionTodos: "Todos los estados",
      onChange: (v: string) => { setEstadoFiltro(v); onFiltroChange() }, opciones: ESTADO_OPCIONES },
  ]

  const filtros: AsignacionesCapacitacionFiltros = {
    empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined,
    areaId: areaFiltro || undefined,
    empleadoId: empleadoFiltro || undefined,
    capacitacionId: capacitacionFiltro || undefined,
    estado: estadoFiltro || undefined,
  }
  return { empresaActivaId, filtros, campos }
}
