/**
 * Estado de los filtros de empleados: qué eligió el usuario. El search se DEBOUNCEA acá:
 * `debouncedSearch` es lo que la página usa para el fetch, y el reset de página (via
 * `onFiltroChange`) se dispara junto con el commit del debounce — mismo tick, un solo fetch,
 * sin perder el reset. Los demás filtros resetean página en su onChange inmediato.
 *
 * Las otras dos mitades viven aparte, y por el mismo motivo: eran lo que hacía crecer este
 * archivo con cada filtro nuevo, y ya lo tenían sobre el límite de 80.
 *   · _catalogosEmpleados.ts — carga de empresas/áreas/proyectos que llenan los selects.
 *   · _camposEmpleados.ts    — la descripción de los controles para <FiltersBar>.
 *
 * 🔴 `sin_manager` se SIEMBRA desde la querystring: es el destino de la alerta agregada del
 * dashboard, y sin la siembra el link aterrizaría en el listado completo — que es justo lo que
 * la alerta viene a evitar. `useSearchParams` obliga a una barrera de Suspense arriba; el
 * porqué está en la página (sin ella `next build` falla, y en dev no se nota).
 *
 * 🚩 SIEMBRA ≠ ESTADO EN LA URL, Y POR ESO EL ATRÁS DEL NAVEGADOR NO FUNCIONA. Esto lee la
 * querystring UNA vez (el inicializador de `useState`) y nunca la escribe. Está bien elegido
 * para un link de ENTRADA —si el valor se releyera, cambiar el filtro a mano quedaría peleando
 * contra la URL— pero no puede sostener el botón Atrás: para eso el valor tiene que DERIVARSE de
 * la URL en cada render. Se analizó el 25/8/2026 al pedido de poner la paginación en la URL y se
 * decidió NO hacerlo todavía. **El análisis completo está en `docs/DEUDA-TECNICA.md` §0.nueva**,
 * incluida la advertencia de por qué la media —sólo la página a la URL— es la opción MALA.
 */
import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"

import { useCatalogosEmpleados } from "./_catalogosEmpleados"
import { construirCampos } from "./_camposEmpleados"

/** "true"/"false" del query param → el "si"/"no"/"" que usa el select. Todo lo demás, "". */
function semilla(valor: string | null): string {
  return valor === "true" ? "si" : valor === "false" ? "no" : ""
}

export function useFiltrosEmpleados(onFiltroChange: () => void) {
  const searchParams = useSearchParams()
  const [proyectoFiltro, setProyectoFiltro] = useState("")
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [areaFiltro, setAreaFiltro] = useState("")
  // `estado` también se siembra: el href de la alerta agregada lleva estado=activo&sin_manager=true
  // y los DOS filtros tienen que aterrizar puestos. Con solo `sin_manager` la pantalla mostraría
  // más filas que las que anuncia la alerta — que es justo el desajuste que la alerta evita.
  const [estadoFiltro, setEstadoFiltro] = useState(() => searchParams.get("estado") ?? "")
  // "" = sin filtro · "si"/"no" → true/false. Se guarda como texto porque el control es un
  // select; la traducción a booleano se hace una sola vez, abajo, al armar `esLider`.
  const [liderFiltro, setLiderFiltro] = useState("")
  // Mismo tri-estado que liderFiltro. El inicializador de useState corre una sola vez: la
  // querystring siembra el valor de arranque y a partir de ahí manda el select, así que
  // cambiar el filtro a mano NO queda peleando contra la URL.
  const [sinManagerFiltro, setSinManagerFiltro] = useState(() => semilla(searchParams.get("sin_manager")))
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")

  const { empresaActivaId, empresas, areas, proyectos } = useCatalogosEmpleados(empresaFiltro)

  // Debounce del search: commitea el valor y resetea la página en el mismo tick (un solo fetch).
  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); onFiltroChange() }, 350)
    return () => clearTimeout(t)
  }, [search])  // eslint-disable-line react-hooks/exhaustive-deps

  const campos = construirCampos({
    search, setSearch, empresaActivaId, empresas, empresaFiltro, setEmpresaFiltro,
    areas, areaFiltro, setAreaFiltro, estadoFiltro, setEstadoFiltro,
    liderFiltro, setLiderFiltro, sinManagerFiltro, setSinManagerFiltro,
    proyectos, proyectoFiltro, setProyectoFiltro, onFiltroChange,
  })

  const empresaOverride = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined
  // `false` es un filtro válido (solo no-líderes), así que no se puede colapsar con `|| undefined`.
  const esLider = liderFiltro === "" ? undefined : liderFiltro === "si"
  const sinManager = sinManagerFiltro === "" ? undefined : sinManagerFiltro === "si"
  return { empresaActivaId, empresaOverride, areaFiltro, estadoFiltro, esLider, sinManager, proyectoId: proyectoFiltro || undefined, debouncedSearch, campos }
}
