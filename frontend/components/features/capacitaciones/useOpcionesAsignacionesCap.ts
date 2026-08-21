/**
 * Carga las OPCIONES de los selects de filtro de asignaciones de formación (empresas, áreas,
 * colaboradores y el catálogo de cursos). Sólo trae datos: no tiene estado de filtro ni arma
 * campos.
 *
 * Salió de `useFiltrosAsignacionesCap`, que estaba en **89 líneas contra un límite de 80 para
 * hooks** —deuda anotada en CLAUDE.md— y al que ni siquiera alcanzaba con mudarle el armado de
 * los campos. Es el MISMO corte que ya tienen ausencias y vacaciones, y por el mismo motivo: acá
 * vive "qué se puede elegir" (que depende de la empresa y se recarga solo) y allá "qué está
 * elegido" (que es estado de UI puro).
 *
 * `empresaFiltro` entra por parámetro porque las opciones dependen de él: en modo consolidado,
 * elegir una empresa recarga áreas, colaboradores y cursos.
 */
import { useEffect, useState } from "react"

import { fetchAreas } from "@/services/areas"
import { fetchCapacitaciones } from "@/services/capacitaciones"
import { fetchEmpleadosSeleccionables } from "@/services/empleados"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Area } from "@/types/area"
import type { Capacitacion } from "@/types/capacitacion"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"

export function useOpcionesAsignacionesCap(empresaFiltro: string) {
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [empleados, setEmpleados] = useState<EmpleadoSeleccionable[]>([])
  const [capacitaciones, setCapacitaciones] = useState<Capacitacion[]>([])

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

  return { empresaActivaId, empresas, areas, empleados, capacitaciones }
}
