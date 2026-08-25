import { etiquetaArea } from "@/components/features/shared/filtros"
import type { FiltroCampo, RangoFechas } from "@/components/ui/FiltersBar"
import type { Area } from "@/types/area"
import type { TipoAusencia } from "@/types/ausencias"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"
import type { Proyecto } from "@/types/proyecto"

/**
 * Armado del array de <FiltersBar> para el listado de ausencias. Extraído de
 * `useFiltrosAusencias.ts` por lo mismo que `_camposEmpleados.ts` salió de su hook: es la lista
 * que crece con cada filtro nuevo, y **es lo único que un test puede ejercitar sin DOM**. Contra
 * campos inventados, el chip llamaría a un `onChange` de mentira y el test pasaría con el
 * cableado roto — el falso verde que CLAUDE.md documenta.
 *
 * 🔴 QUÉ QUEDA DETRÁS DE "MÁS FILTROS" Y POR QUÉ ESTOS DOS. La fila superior del panel (§3) es
 * "buscador, selectores de 30px y un 'Más filtros' para el resto", y quién es el resto lo decide
 * cada pantalla, nunca la posición. Acá la pregunta diaria es del MES: "¿quiénes faltaron en
 * marzo, de qué área y de qué tipo?" — por eso Empresa, Área, Tipo y Período quedan a la vista.
 * **Colaborador** es un recorte a UNA persona, y esa pregunta ya tiene su lugar propio en la ficha
 * del legajo; **Proyecto** cruza con otro módulo, igual que en /empleados. Los dos siguen a un
 * click y, si vienen puestos, el panel arranca abierto y además los delata su chip.
 *
 * Sin estado ni efectos: recibe valores y setters, devuelve la descripción de los controles. El
 * reset de página lo dispara `onFiltroChange` en cada onChange (invariante 4 del bloque B).
 */
export interface ArgsCamposAusencias {
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
  tipos: TipoAusencia[]
  tipoFiltro: string
  setTipoFiltro: (v: string) => void
  rango: RangoFechas
  setRango: (v: RangoFechas) => void
  proyectos: Proyecto[]
  proyectoFiltro: string
  setProyectoFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCampos(a: ArgsCamposAusencias): FiltroCampo[] {
  return [
    ...((!a.empresaActivaId && a.empresas.length > 0) || a.empresaFiltro ? [{ tipo: "select" as const, label: "Empresa", value: a.empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { a.setEmpresaFiltro(v); a.setAreaFiltro(""); a.setEmpleadoFiltro(""); a.onFiltroChange() },
      opciones: a.empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    ...((a.areas.length > 0) || a.areaFiltro ? [{ tipo: "select" as const, label: "Área", value: a.areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { a.setAreaFiltro(v); a.onFiltroChange() },
      opciones: a.areas.map((ar) => ({ value: ar.id, label: etiquetaArea(ar, a.empresas, Boolean(a.empresaActivaId || a.empresaFiltro)) })) }] : []),
    // Elegir un PADRE trae también las ausencias de sus hijos: la familia la resuelve el
    // backend (`AusenciasService.get_all`), que es el mismo punto por el que pasa el export.
    // Acá solo se etiqueta el subtipo con su padre para que la lista se lea en dos niveles.
    ...((a.tipos.length > 0) || a.tipoFiltro ? [{ tipo: "select" as const, label: "Tipo", value: a.tipoFiltro, opcionTodos: "Todos los tipos",
      onChange: (v: string) => { a.setTipoFiltro(v); a.onFiltroChange() },
      opciones: a.tipos.map((t) => ({ value: t.id, label: t.padre_nombre ? `${t.padre_nombre} › ${t.nombre}` : t.nombre })) }] : []),
    { tipo: "daterange" as const, label: "Período", value: a.rango,
      onChange: (v: RangoFechas) => { a.setRango(v); a.onFiltroChange() } },
    ...((a.empleadosSel.length > 0) || a.empleadoFiltro ? [{ tipo: "select" as const, label: "Colaborador", value: a.empleadoFiltro, opcionTodos: "Todos los colaboradores", avanzado: true,
      onChange: (v: string) => { a.setEmpleadoFiltro(v); a.onFiltroChange() },
      opciones: a.empleadosSel.map((e) => ({ value: e.id, label: `${e.apellido}, ${e.nombre}` })) }] : []),
    ...((a.proyectos.length > 0) || a.proyectoFiltro ? [{ tipo: "select" as const, label: "Proyecto", value: a.proyectoFiltro, opcionTodos: "Todos los proyectos", avanzado: true,
      onChange: (v: string) => { a.setProyectoFiltro(v); a.onFiltroChange() },
      opciones: a.proyectos.map((p) => ({ value: p.id, label: p.nombre })) }] : []),
  ]
}
