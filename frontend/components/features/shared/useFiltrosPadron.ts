/**
 * Estado de los filtros de las pantallas del PADRÓN que no eligen estado: `/proximos-ingresos` y
 * `/bajas`. Un solo hook para las dos, porque filtran exactamente lo mismo (nombre, empresa,
 * área) y lo único que cambia entre ellas —el `estado` y el `orden`— lo pone la página.
 *
 * Molde: `useFiltrosEmpleados`, del que copia las dos decisiones que ya estaban resueltas ahí:
 *   · el search se DEBOUNCEA acá, y el reset de página viaja con el commit del debounce (mismo
 *     tick, un solo fetch, sin perder el reset — invariante 4 del bloque B);
 *   · el armado de los controles vive aparte (`_camposPadron.ts`), que es lo que hace crecer el
 *     archivo con cada filtro nuevo.
 *
 * ⚠️ NO siembra nada de la querystring, a diferencia de `useFiltrosEmpleados`. Ese hook lo hace
 * porque la alerta agregada del dashboard linkea a `/empleados?sin_manager=true`; a estas dos
 * pantallas no linkea nadie con filtros puestos todavía. El día que pase, se copia la siembra de
 * allá —incluida la barrera de Suspense que `useSearchParams` obliga a poner arriba.
 */
import { useEffect, useState } from "react"

import { useCatalogosEmpleados } from "@/components/features/empleados/_catalogosEmpleados"
import { construirCamposPadron } from "@/components/features/shared/_camposPadron"

export function useFiltrosPadron(onFiltroChange: () => void, placeholderBusqueda: string) {
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [areaFiltro, setAreaFiltro] = useState("")
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")

  // `false`: estas pantallas no filtran por proyecto, así que no se pide ese catálogo.
  const { empresaActivaId, empresas, areas } = useCatalogosEmpleados(empresaFiltro, false)

  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); onFiltroChange() }, 350)
    return () => clearTimeout(t)
  }, [search])  // eslint-disable-line react-hooks/exhaustive-deps

  const campos = construirCamposPadron({
    search, setSearch, empresaActivaId, empresas, empresaFiltro, setEmpresaFiltro,
    areas, areaFiltro, setAreaFiltro, onFiltroChange, placeholderBusqueda,
  })

  // Solo en modo consolidado el filtro de empresa manda: con una empresa activa en el sidebar,
  // el header ya la lleva y un override acá la pisaría con la de un select que no se muestra.
  const empresaOverride = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined

  return { empresaActivaId, empresaOverride, areaFiltro, debouncedSearch, campos }
}
