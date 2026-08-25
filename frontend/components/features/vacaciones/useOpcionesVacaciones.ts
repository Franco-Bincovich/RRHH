/**
 * Carga las OPCIONES de los selects de filtro de vacaciones (empresas, áreas, colaboradores,
 * proyectos). Solo trae datos: no tiene estado de filtro ni arma campos.
 *
 * Extraído de `useFiltrosVacaciones`, que estaba en **95 líneas contra un límite de 80 para
 * hooks** (deuda anotada en CLAUDE.md). El corte es el MISMO que ya tenía la pantalla hermana
 * —`useOpcionesAusencias`— y por el mismo motivo: acá vive "qué se puede elegir" (que depende de
 * la empresa y se recarga sola) y allá "qué está elegido" (que es estado de UI puro).
 *
 * ⚠️ Es una COPIA casi literal del de ausencias, con una diferencia real: acá no hay catálogo de
 * tipos. Unificarlos exigiría un hook con opciones opcionales, que es la forma de que un cambio
 * en una pantalla se filtre a la otra sin que nadie lo mire.
 *
 * `empresaFiltro` entra por parámetro porque las opciones dependen de él: en modo consolidado,
 * elegir una empresa recarga áreas, colaboradores y proyectos.
 */
import { useEffect, useState } from "react"

import { useCatalogoPermitido } from "@/hooks/useCatalogoPermitido"
import { fetchAreas } from "@/services/areas"
import { fetchEmpleadosSeleccionables } from "@/services/empleados"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { fetchEmpresas } from "@/services/empresas"
import { fetchProyectos } from "@/services/proyectos"
import type { Area } from "@/types/area"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"
import type { Proyecto } from "@/types/proyecto"

export function useOpcionesVacaciones(empresaFiltro: string) {
  // 🔴 Un catálogo que el rol no puede leer no se pide: `mandos_medios` SÍ ve esta pantalla pero
  // NO tiene lectura de empresas, áreas ni proyectos, así que cada carga eran tres 403 tragados
  // por los `.catch`. Ver `hooks/useCatalogoPermitido`.
  const puedeEmpresas = useCatalogoPermitido("empresa")
  const puedeAreas = useCatalogoPermitido("areas")
  const puedeProyectos = useCatalogoPermitido("proyectos")
  const [empresaActivaId, setEmpresaActivaId] = useState<string | null>(null)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [empleadosSel, setEmpleadosSel] = useState<EmpleadoSeleccionable[]>([])
  const [proyectos, setProyectos] = useState<Proyecto[]>([])

  useEffect(() => {
    const id = getEmpresaActivaId()
    setEmpresaActivaId(id)
    if (!id && puedeEmpresas) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [puedeEmpresas])

  useEffect(() => {
    const empId = empresaActivaId || empresaFiltro || undefined
    if (puedeAreas) fetchAreas(empId).then(setAreas).catch(() => setAreas([]))
    // El selector no necesita etiquetaProyecto: hoy no hay nombres de proyecto repetidos
    // entre empresas. Si algún día los hay, reusar el patrón de shared/filtros.ts.
    if (puedeProyectos) {
      fetchProyectos({ empresaIdOverride: empId })
        .then((r) => setProyectos(r.items)).catch(() => setProyectos([]))
    }
  }, [empresaActivaId, empresaFiltro, puedeAreas, puedeProyectos])

  useEffect(() => {
    const empId = empresaActivaId || empresaFiltro
    if (!empId) { setEmpleadosSel([]); return }
    fetchEmpleadosSeleccionables(empId).then(setEmpleadosSel).catch(() => setEmpleadosSel([]))
  }, [empresaActivaId, empresaFiltro])

  return { empresaActivaId, empresas, areas, empleadosSel, proyectos }
}
