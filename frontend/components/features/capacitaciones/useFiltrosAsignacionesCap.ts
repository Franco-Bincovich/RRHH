/**
 * Estado de los filtros de asignaciones de formación: qué eligió el usuario. Sigue el molde de
 * components/features/shared/filtros.ts: un solo objeto de filtros que consumen el listado Y el
 * export, así no pueden divergir.
 *
 * `onFiltroChange` se dispara en cada cambio; la pestaña lo cablea a resetear la paginación
 * (invariante 4 del bloque B).
 *
 * ⚠️ ESTE ARCHIVO ESTABA EN 89 LÍNEAS CONTRA UN LÍMITE DE 80 —deuda anotada en CLAUDE.md— y al
 * migrar la pantalla al patrón del bloque B se partió en las mismas dos mitades que ya tenían
 * ausencias y vacaciones:
 *   · `useOpcionesAsignacionesCap` — carga de empresas/áreas/colaboradores/cursos.
 *   · `_camposCapacitaciones.ts`   — la descripción de los controles para <FiltersBar>, y **lo
 *     único que un test puede ejercitar sin DOM**: los chips se prueban contra esa función.
 */
import { useState } from "react"

import { construirCamposAsignacionesCap } from "@/components/features/capacitaciones/_camposCapacitaciones"
import { useOpcionesAsignacionesCap } from "@/components/features/capacitaciones/useOpcionesAsignacionesCap"
import type { AsignacionesCapacitacionFiltros } from "@/services/capacitaciones"

export function useFiltrosAsignacionesCap(onFiltroChange: () => void) {
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [areaFiltro, setAreaFiltro] = useState("")
  const [empleadoFiltro, setEmpleadoFiltro] = useState("")
  const [capacitacionFiltro, setCapacitacionFiltro] = useState("")
  const [estadoFiltro, setEstadoFiltro] = useState("")

  const { empresaActivaId, empresas, areas, empleados, capacitaciones } =
    useOpcionesAsignacionesCap(empresaFiltro)

  /** Cambiar de empresa limpia área, colaborador y formación: los tres son de UNA empresa, y
   *  dejarlos puestos deja el listado en cero sin que nada lo explique. */
  const cambiarEmpresa = (v: string) => {
    setEmpresaFiltro(v); setAreaFiltro(""); setEmpleadoFiltro(""); setCapacitacionFiltro("")
  }

  const campos = construirCamposAsignacionesCap({
    empresaActivaId, empresas, empresaFiltro, cambiarEmpresa,
    areas, areaFiltro, setAreaFiltro, estadoFiltro, setEstadoFiltro,
    empleados, empleadoFiltro, setEmpleadoFiltro,
    capacitaciones, capacitacionFiltro, setCapacitacionFiltro, onFiltroChange,
  })

  const filtros: AsignacionesCapacitacionFiltros = {
    empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined,
    areaId: areaFiltro || undefined,
    empleadoId: empleadoFiltro || undefined,
    capacitacionId: capacitacionFiltro || undefined,
    estado: estadoFiltro || undefined,
  }
  return { empresaActivaId, filtros, campos }
}
