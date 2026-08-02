/**
 * Carga las OPCIONES de los selects de filtro de ausencias (empresas, áreas, empleados, tipos,
 * proyectos). Solo trae datos: no tiene estado de filtro ni arma campos.
 *
 * Extraído de `useFiltrosAusencias`, que estaba en 93 contra un límite de 80 para hooks — el
 * único archivo del repo que ya estaba over-limit sin figurar en la deuda de CLAUDE.md.
 *
 * El corte es por responsabilidad, no por líneas: acá vive "qué se puede elegir" (que depende de
 * la empresa y se recarga sola) y allá "qué está elegido" (que es estado de UI puro). Sin la
 * separación, el hook de filtros crece con cada select nuevo aunque el estado del filtro sea
 * siempre el mismo — y con la jerarquía de tipos viene otro.
 *
 * `empresaFiltro` entra por parámetro porque las opciones dependen de él: en modo consolidado,
 * elegir una empresa recarga áreas, empleados y proyectos.
 */
import { useEffect, useState } from "react"

import { fetchAreas } from "@/services/areas"
import { fetchTiposAusencia } from "@/services/ausencias"
import { fetchEmpleadosSeleccionables } from "@/services/empleados"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { fetchEmpresas } from "@/services/empresas"
import { fetchProyectos } from "@/services/proyectos"
import type { Area } from "@/types/area"
import type { TipoAusencia } from "@/types/ausencias"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"
import type { Proyecto } from "@/types/proyecto"

export function useOpcionesAusencias(empresaFiltro: string) {
  const [empresaActivaId, setEmpresaActivaId] = useState<string | null>(null)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [empleadosSel, setEmpleadosSel] = useState<EmpleadoSeleccionable[]>([])
  const [tipos, setTipos] = useState<TipoAusencia[]>([])
  const [proyectos, setProyectos] = useState<Proyecto[]>([])

  useEffect(() => {
    const id = getEmpresaActivaId()
    setEmpresaActivaId(id)
    if (!id) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
    fetchTiposAusencia().then((r) => setTipos(r.items)).catch(() => {})
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

  return { empresaActivaId, empresas, areas, empleadosSel, tipos, proyectos }
}
