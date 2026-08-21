/**
 * Estado de los filtros de ausencias: qué eligió el usuario. `onFiltroChange` se dispara en cada
 * cambio (la página lo usa para resetear la paginación a 1). El select de colaborador solo
 * aparece con empresa definida (igual que áreas).
 *
 * Las otras dos mitades viven aparte, y por el mismo motivo que en /empleados: eran lo que hacía
 * crecer este archivo con cada filtro nuevo.
 *   · _opcionesAusencias  — carga de empresas/áreas/colaboradores/tipos/proyectos (useOpciones…).
 *   · _camposAusencias.ts — la descripción de los controles para <FiltersBar>, y **lo único que
 *     un test puede ejercitar sin DOM**: los chips se prueban contra esa función, no contra
 *     campos inventados.
 */
import { useState } from "react"

import { useOpcionesAusencias } from "@/components/features/ausencias/useOpcionesAusencias"
import { construirCampos } from "@/components/features/ausencias/_camposAusencias"
import type { RangoFechas } from "@/components/ui/FiltersBar"
import type { AusenciasFiltros } from "@/services/ausencias"

export function useFiltrosAusencias(onFiltroChange: () => void) {
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [areaFiltro, setAreaFiltro] = useState("")
  const [empleadoFiltro, setEmpleadoFiltro] = useState("")
  const [tipoFiltro, setTipoFiltro] = useState("")
  const [proyectoFiltro, setProyectoFiltro] = useState("")
  const [rango, setRango] = useState<RangoFechas>({ desde: "", hasta: "" })

  const { empresaActivaId, empresas, areas, empleadosSel, tipos, proyectos } =
    useOpcionesAusencias(empresaFiltro)

  const campos = construirCampos({
    empresaActivaId, empresas, empresaFiltro, setEmpresaFiltro,
    areas, areaFiltro, setAreaFiltro,
    empleadosSel, empleadoFiltro, setEmpleadoFiltro,
    tipos, tipoFiltro, setTipoFiltro,
    rango, setRango, proyectos, proyectoFiltro, setProyectoFiltro, onFiltroChange,
  })

  // Un solo objeto de filtros: lo consumen el listado y el export, así que no pueden divergir.
  const filtros: AusenciasFiltros = {
    empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined,
    areaId: areaFiltro || undefined,
    tipoId: tipoFiltro || undefined,
    empleadoId: empleadoFiltro || undefined,
    fechaDesde: rango.desde || undefined,
    fechaHasta: rango.hasta || undefined,
    proyectoId: proyectoFiltro || undefined,
  }
  return { empresaActivaId, filtros, campos }
}
