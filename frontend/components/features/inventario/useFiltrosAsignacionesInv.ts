/**
 * Estado de los filtros de asignaciones de inventario + carga de opciones + armado del array
 * de FiltroCampo para <FiltersBar>. Sigue el molde de components/features/shared/filtros.ts:
 * un solo objeto de filtros que consumen el listado Y el export, así no pueden divergir.
 *
 * `onFiltroChange` se dispara en cada cambio y la pestaña lo cablea a volver a la página 1
 * (invariante 4 del bloque B).
 *
 * ⚠️ ACÁ DECÍA "este listado no pagina hoy". **Sí pagina**: `GET /api/inventario/asignaciones`
 * acepta `page`/`page_size` y `AsignacionesTab` dibuja su barra. El comentario quedó viejo y se
 * corrigió, porque de él se deduce mal la próxima decisión — por ejemplo, contar sobre el array
 * en vez de leer el `total` del backend.
 *
 * ⚠️ El ARMADO de los campos se mudó a `_camposInventario.ts` al migrar la pantalla al patrón del
 * bloque B: es lo único que un test puede ejercitar sin DOM, y ahí vive la decisión de qué filtro
 * queda detrás de "Más filtros".
 */
import { useEffect, useState } from "react"

import { construirCamposAsignaciones } from "@/components/features/inventario/_camposInventario"
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

  /** Cambiar de empresa limpia área y colaborador: los dos son de UNA empresa, y dejarlos
   *  puestos deja el listado en cero sin que nada lo explique. */
  const cambiarEmpresa = (v: string) => { setEmpresaFiltro(v); setEmpleadoFiltro(""); setAreaFiltro("") }

  const campos = construirCamposAsignaciones({
    empresaActivaId, empresas, empresaFiltro, cambiarEmpresa,
    areas, areaFiltro, setAreaFiltro,
    empleados, empleadoFiltro, setEmpleadoFiltro, onFiltroChange,
  })

  const filtros: AsignacionesInventarioFiltros = {
    empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined,
    empleadoId: empleadoFiltro || undefined,
    areaId: areaFiltro || undefined,
  }
  return { empresaActivaId, filtros, campos }
}
