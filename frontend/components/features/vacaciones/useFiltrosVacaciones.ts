/**
 * Estado de los filtros de vacaciones: qué eligió el usuario. `onFiltroChange` se dispara en cada
 * cambio (la página lo usa para resetear la paginación a 1). El select de colaborador solo
 * aparece con empresa definida (igual que áreas). El estado tiene opciones fijas
 * (planificada/tomada/cancelada) y se filtra server-side.
 *
 * ⚠️ Este archivo estaba en **95 líneas contra un límite de 80 para hooks** —deuda anotada en
 * CLAUDE.md— y al migrar la pantalla al patrón del bloque B se partió en las mismas dos mitades
 * que ya tenía la pantalla hermana:
 *   · _opcionesVacaciones (useOpciones…) — carga de empresas/áreas/colaboradores/proyectos.
 *   · _camposVacaciones.ts — la descripción de los controles para <FiltersBar>, y **lo único que
 *     un test puede ejercitar sin DOM**: los chips se prueban contra esa función.
 */
import { useState } from "react"

import { construirCampos } from "@/components/features/vacaciones/_camposVacaciones"
import { useOpcionesVacaciones } from "@/components/features/vacaciones/useOpcionesVacaciones"
import type { RangoFechas } from "@/components/ui/FiltersBar"
import type { VacacionesFiltros } from "@/services/vacaciones"

export function useFiltrosVacaciones(onFiltroChange: () => void) {
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [areaFiltro, setAreaFiltro] = useState("")
  const [empleadoFiltro, setEmpleadoFiltro] = useState("")
  const [estadoFiltro, setEstadoFiltro] = useState("")
  const [proyectoFiltro, setProyectoFiltro] = useState("")
  const [rango, setRango] = useState<RangoFechas>({ desde: "", hasta: "" })

  const { empresaActivaId, empresas, areas, empleadosSel, proyectos } =
    useOpcionesVacaciones(empresaFiltro)

  const campos = construirCampos({
    empresaActivaId, empresas, empresaFiltro, setEmpresaFiltro,
    areas, areaFiltro, setAreaFiltro,
    empleadosSel, empleadoFiltro, setEmpleadoFiltro,
    estadoFiltro, setEstadoFiltro,
    rango, setRango, proyectos, proyectoFiltro, setProyectoFiltro, onFiltroChange,
  })

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
