import { useEffect, useState } from "react"

import { fetchAreas } from "@/services/areas"
import { fetchEmpresas } from "@/services/empresas"
import { fetchProyectos } from "@/services/proyectos"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"
import type { Proyecto } from "@/types/proyecto"

/**
 * Catálogos que llenan los selects del filtro de empleados: empresas, áreas y proyectos.
 * Separado de useFiltrosEmpleados —que quedaba en 86 líneas contra un límite de 80 para
 * hooks— porque es otra responsabilidad: acá se CARGAN opciones, allá se guarda qué eligió
 * el usuario. Ninguna de las dos crece por la otra.
 *
 * `empresaFiltro` entra como argumento en vez de vivir acá porque es un filtro elegido por
 * el usuario, no un catálogo: su dueño es el hook de filtros. Este solo lo necesita para
 * saber de qué empresa pedir áreas y proyectos cuando se está en modo consolidado.
 */
export function useCatalogosEmpleados(empresaFiltro: string) {
  const [empresaActivaId, setEmpresaActivaId] = useState<string | null>(null)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [proyectos, setProyectos] = useState<Proyecto[]>([])

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

  return { empresaActivaId, empresas, areas, proyectos }
}
