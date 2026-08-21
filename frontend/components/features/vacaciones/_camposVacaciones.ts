import { etiquetaArea } from "@/components/features/shared/filtros"
import type { FiltroCampo, RangoFechas } from "@/components/ui/FiltersBar"
import type { Area } from "@/types/area"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"
import type { Proyecto } from "@/types/proyecto"

/**
 * Armado del array de <FiltersBar> para el listado de vacaciones. Extraído de
 * `useFiltrosVacaciones.ts`, que estaba en **95 líneas contra un límite de 80 para hooks** (deuda
 * anotada en CLAUDE.md) y es justamente esta lista la que crecía con cada filtro nuevo. Y además
 * **es lo único que un test puede ejercitar sin DOM**: los chips se prueban contra esta función,
 * no contra campos inventados — con campos de mentira el chip llamaría a un `onChange` de mentira
 * y el test pasaría con el cableado roto.
 *
 * 🔴 QUÉ QUEDA DETRÁS DE "MÁS FILTROS" Y POR QUÉ ESTOS DOS. Quién es avanzado lo decide cada
 * pantalla, nunca la posición del campo. La pregunta diaria de vacaciones es del PERÍODO y del
 * ESTADO: "¿quién está de vacaciones en enero?", "¿qué quedó planificado y no se tomó?" — por eso
 * Empresa, Área, Estado y Período quedan a la vista. **Colaborador** es un recorte a UNA persona,
 * que además tiene su propio saldo e histórico en la ficha del legajo; **Proyecto** cruza con otro
 * módulo, igual que en /empleados. Los dos siguen a un click y, si vienen puestos, el panel
 * arranca abierto y además los delata su chip.
 *
 * Sin estado ni efectos: recibe valores y setters, devuelve la descripción de los controles. El
 * reset de página lo dispara `onFiltroChange` en cada onChange (invariante 4 del bloque B).
 */
export const ESTADO_OPCIONES = [
  { value: "planificada", label: "Planificada" },
  { value: "tomada", label: "Tomada" },
  { value: "cancelada", label: "Cancelada" },
]

export interface ArgsCamposVacaciones {
  empresaActivaId: string | null
  empresas: Empresa[]
  empresaFiltro: string
  setEmpresaFiltro: (v: string) => void
  areas: Area[]
  areaFiltro: string
  setAreaFiltro: (v: string) => void
  empleadosSel: EmpleadoSeleccionable[]
  empleadoFiltro: string
  setEmpleadoFiltro: (v: string) => void
  estadoFiltro: string
  setEstadoFiltro: (v: string) => void
  rango: RangoFechas
  setRango: (v: RangoFechas) => void
  proyectos: Proyecto[]
  proyectoFiltro: string
  setProyectoFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCampos(a: ArgsCamposVacaciones): FiltroCampo[] {
  return [
    ...(!a.empresaActivaId && a.empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: a.empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { a.setEmpresaFiltro(v); a.setAreaFiltro(""); a.setEmpleadoFiltro(""); a.onFiltroChange() },
      opciones: a.empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    ...(a.areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: a.areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { a.setAreaFiltro(v); a.onFiltroChange() },
      opciones: a.areas.map((ar) => ({ value: ar.id, label: etiquetaArea(ar, a.empresas, Boolean(a.empresaActivaId || a.empresaFiltro)) })) }] : []),
    { tipo: "select" as const, label: "Estado", value: a.estadoFiltro, opcionTodos: "Todos los estados",
      onChange: (v: string) => { a.setEstadoFiltro(v); a.onFiltroChange() }, opciones: ESTADO_OPCIONES },
    { tipo: "daterange" as const, label: "Período", value: a.rango,
      onChange: (v: RangoFechas) => { a.setRango(v); a.onFiltroChange() } },
    ...(a.empleadosSel.length > 0 ? [{ tipo: "select" as const, label: "Colaborador", value: a.empleadoFiltro, opcionTodos: "Todos los colaboradores", avanzado: true,
      onChange: (v: string) => { a.setEmpleadoFiltro(v); a.onFiltroChange() },
      opciones: a.empleadosSel.map((e) => ({ value: e.id, label: `${e.apellido}, ${e.nombre}` })) }] : []),
    ...(a.proyectos.length > 0 ? [{ tipo: "select" as const, label: "Proyecto", value: a.proyectoFiltro, opcionTodos: "Todos los proyectos", avanzado: true,
      onChange: (v: string) => { a.setProyectoFiltro(v); a.onFiltroChange() },
      opciones: a.proyectos.map((p) => ({ value: p.id, label: p.nombre })) }] : []),
  ]
}
