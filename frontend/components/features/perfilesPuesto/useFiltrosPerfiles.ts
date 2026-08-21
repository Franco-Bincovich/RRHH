import { useEffect, useMemo, useState } from "react"

import type { FiltroCampo } from "@/components/ui/FiltersBar"
import type { PerfilesFiltros } from "@/services/perfilesPuesto"

/**
 * Los DOS filtros del catálogo de perfiles, y no hay más.
 *
 * 🔴 NO SE INVENTAN FILTROS QUE EL BACKEND NO TIENE. El listado acepta exactamente `search`
 * (ilike sobre el nombre) e `incluir_inactivos`. Ofrecer acá un filtro por nivel o por modalidad
 * sería peor que no ofrecerlo: la pantalla filtraría en el cliente sobre la página que llegó, el
 * export —que va server-side— seguiría trayendo todo, y el archivo saldría con más filas de las
 * que se ven. Es la invariante 1 del bloque B.
 *
 * ⚠️ TAMPOCO HAY FILTRO DE EMPRESA: el catálogo es del grupo y ninguna ruta lee `X-Empresa-Id`.
 *
 * El search se DEBOUNCEA acá y el reset de página viaja con el commit del debounce (mismo tick,
 * un solo fetch, sin perder el reset). Molde: `useFiltrosPadron`.
 */
export function useFiltrosPerfiles(onFiltroChange: () => void) {
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [inactivos, setInactivos] = useState("")

  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); onFiltroChange() }, 350)
    return () => clearTimeout(t)
  }, [search])  // eslint-disable-line react-hooks/exhaustive-deps

  // Memorizado sobre los primitivos: `cargarPerfiles` lo lleva en las dependencias de su
  // callback, y un objeto nuevo por render dispararía un fetch por render.
  const filtros = useMemo<PerfilesFiltros>(() => ({
    search: debouncedSearch || undefined,
    incluirInactivos: inactivos === "si",
  }), [debouncedSearch, inactivos])

  const campos: FiltroCampo[] = [
    // Se llama "Nombre" y no "Buscar" porque el backend busca SOLO sobre el nombre. Además es lo
    // que hace legible el estado vacío, que arma la frase con la etiqueta del chip: "No hay
    // perfiles de puesto con nombre analista" se entiende; "con buscar analista", no.
    {
      tipo: "search", label: "Nombre", value: search,
      // El buscador comparte la fila con el selector de bajas: con el texto largo el placeholder
      // se cortaba a la mitad ("Buscar por nombre del per"), en desktop Y en mobile. Es el mismo
      // texto que ya usa el listado de colaboradores.
      placeholder: "Buscar por nombre...", onChange: setSearch,
    },
    {
      tipo: "select", label: "Bajas", value: inactivos, opcionTodos: "Solo activos",
      onChange: (v: string) => { setInactivos(v); onFiltroChange() },
      opciones: [{ value: "si", label: "Incluir las dadas de baja" }],
    },
  ]

  return { filtros, campos }
}
