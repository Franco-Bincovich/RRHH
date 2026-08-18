import { etiquetaArea } from "@/components/features/shared/filtros"
import type { FiltroCampo } from "@/components/ui/FiltersBar"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"
import type { Proyecto } from "@/types/proyecto"

/**
 * Armado del array de <FiltersBar> para el listado de empleados. Extraído de
 * useFiltrosEmpleados.ts, que estaba en 89 líneas contra un límite de 80 para hooks — y es
 * justamente esta lista la que crece con cada filtro nuevo, así que dejarla adentro garantizaba
 * volver a pasarse en el próximo.
 *
 * Sin estado ni efectos: recibe valores y setters, devuelve la descripción de los controles.
 * El reset de página lo dispara `onFiltroChange` en cada onChange (invariante 4 del bloque B);
 * el search es la excepción, porque su reset viaja con el commit del debounce, en el hook.
 */
export const LIDER_OPCIONES = [
  { value: "si", label: "Solo líderes" },
  { value: "no", label: "Solo no líderes" },
]

// ⚠️ NO es el espejo del CHECK — es la lista de lo que se OFRECE FILTRAR, y son dos cosas
// distintas. `preingreso` entra porque desde la migración 120 hay fichas en ese estado y el
// listado, por default, NO las trae (`_empleado_row.filtro_estado`): sin esta opción no habría
// forma de verlas desde la UI.
// `suspendido` NO entra, aunque el CHECK lo acepte: ningún camino del backend lo escribe (está
// declarado como valor muerto en `utils/estados_empleado.py`), y ofrecer en un select un filtro
// que siempre devuelve cero es peor que no ofrecerlo — el usuario no puede distinguir "no hay
// nadie suspendido" de "el filtro está roto". Entra el día que algo lo escriba.
export const ESTADO_OPCIONES = [
  { value: "activo", label: "Activo" },
  { value: "preingreso", label: "Preingreso" },
  { value: "baja", label: "Baja" },
  { value: "licencia", label: "Licencia" },
]

export const SUPERIOR_OPCIONES = [
  { value: "si", label: "Sin superior asignado" },
  { value: "no", label: "Con superior asignado" },
]

export interface ArgsCampos {
  search: string
  setSearch: (v: string) => void
  empresaActivaId: string | null
  empresas: Empresa[]
  empresaFiltro: string
  setEmpresaFiltro: (v: string) => void
  areas: Area[]
  areaFiltro: string
  setAreaFiltro: (v: string) => void
  estadoFiltro: string
  setEstadoFiltro: (v: string) => void
  liderFiltro: string
  setLiderFiltro: (v: string) => void
  sinManagerFiltro: string
  setSinManagerFiltro: (v: string) => void
  proyectos: Proyecto[]
  proyectoFiltro: string
  setProyectoFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCampos(a: ArgsCampos): FiltroCampo[] {
  return [
    { tipo: "search" as const, label: "Buscar", value: a.search, placeholder: "Buscar por nombre...", onChange: a.setSearch },
    ...(!a.empresaActivaId && a.empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: a.empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { a.setEmpresaFiltro(v); a.setAreaFiltro(""); a.onFiltroChange() },
      opciones: a.empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    ...(a.areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: a.areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { a.setAreaFiltro(v); a.onFiltroChange() },
      opciones: a.areas.map((ar) => ({ value: ar.id, label: etiquetaArea(ar, a.empresas, Boolean(a.empresaActivaId || a.empresaFiltro)) })) }] : []),
    { tipo: "select" as const, label: "Estado", value: a.estadoFiltro, opcionTodos: "Todos los estados",
      onChange: (v: string) => { a.setEstadoFiltro(v); a.onFiltroChange() }, opciones: ESTADO_OPCIONES },
    { tipo: "select" as const, label: "Liderazgo", value: a.liderFiltro, opcionTodos: "Todos",
      onChange: (v: string) => { a.setLiderFiltro(v); a.onFiltroChange() }, opciones: LIDER_OPCIONES },
    { tipo: "select" as const, label: "Superior", value: a.sinManagerFiltro, opcionTodos: "Todos",
      onChange: (v: string) => { a.setSinManagerFiltro(v); a.onFiltroChange() }, opciones: SUPERIOR_OPCIONES },
    ...(a.proyectos.length > 0 ? [{ tipo: "select" as const, label: "Proyecto", value: a.proyectoFiltro, opcionTodos: "Todos los proyectos",
      onChange: (v: string) => { a.setProyectoFiltro(v); a.onFiltroChange() },
      opciones: a.proyectos.map((p) => ({ value: p.id, label: p.nombre })) }] : []),
  ]
}
