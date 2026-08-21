/**
 * Estado de los filtros de proyectos + carga de las opciones (empresas, áreas). Sigue el molde de
 * components/features/shared/filtros.ts: un solo objeto de filtros que consumen el listado y el
 * export, que es lo que hace estructuralmente imposible que un filtro quede en una sola punta.
 *
 * `onFiltroChange` se dispara en cada cambio y la página lo cablea a volver a la página 1
 * (invariante 4 del bloque B).
 * ⚠️ Acá decía *"hoy este listado no pagina"*: **sí pagina**. `GET /api/proyectos` acepta
 * `page`/`page_size` desde antes de esta tanda y la pantalla dibuja su barra; el comentario quedó
 * viejo y se corrigió, porque de él se deduce mal la próxima decisión (por ejemplo, contar sobre
 * el array en vez de leer el `total` del backend).
 *
 * ⚠️ El ARMADO de los campos se mudó a `_camposProyectos.ts` al migrar la pantalla al patrón del
 * bloque B: es lo único que un test puede ejercitar sin DOM, y ahí vive la decisión de qué filtro
 * queda detrás de "Más filtros".
 */
import { useEffect, useState } from "react"

import { construirCampos } from "@/components/features/proyectos/_camposProyectos"
import { fetchAreas } from "@/services/areas"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"
import type { ProyectosFiltros } from "@/services/proyectos"

export function useFiltrosProyectos(onFiltroChange: () => void) {
  const [estadoFiltro, setEstadoFiltro] = useState("")
  const [areaFiltro, setAreaFiltro] = useState("")
  const [areas, setAreas] = useState<Area[]>([])
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [empresaFiltro, setEmpresaFiltro] = useState("")

  const empresaId = empresaActivaId || empresaFiltro

  useEffect(() => {
    if (!empresaActivaId) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [empresaActivaId])

  useEffect(() => {
    fetchAreas(empresaId || undefined).then(setAreas).catch(() => setAreas([]))
  }, [empresaId])

  const campos = construirCampos({
    empresaActivaId, empresas, empresaFiltro, setEmpresaFiltro,
    estadoFiltro, setEstadoFiltro, areas, areaFiltro, setAreaFiltro, onFiltroChange,
  })

  const filtros: ProyectosFiltros = {
    empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined,
    estado: estadoFiltro || undefined,
    areaId: areaFiltro || undefined,
  }
  return { filtros, campos }
}
