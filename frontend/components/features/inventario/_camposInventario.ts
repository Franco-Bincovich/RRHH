import { etiquetaArea } from "@/components/features/shared/filtros"
import type { FiltroCampo, OpcionFiltro } from "@/components/ui/FiltersBar"
import type { Area } from "@/types/area"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"

import { ESTADO_ITEM_LABEL } from "./_grillaInventario"

/**
 * Armado de los arrays de <FiltersBar> de las DOS pestañas de /inventario. Aparte de los hooks
 * por lo mismo que en el resto del bloque: **es lo único que un test puede ejercitar sin DOM**,
 * así que los chips se prueban contra el cableado real y no contra campos inventados.
 *
 * 🔴 QUÉ QUEDA DETRÁS DE "MÁS FILTROS", Y POR QUÉ ES DISTINTO EN CADA PESTAÑA. Quién es avanzado
 * lo decide cada pantalla, nunca la posición del campo:
 *
 *   · **Ítems** — la pregunta diaria es del ESTADO ("¿qué hay disponible para asignarle a quien
 *     entra el lunes?"), así que Empresa y Estado quedan a la vista. **Área** es el recorte a otra
 *     entidad —un ítem no tiene área propia, se resuelve por quién lo tiene— y va atrás.
 *   · **Asignaciones** — la pregunta diaria es "¿quién tiene qué?" y el recorte estructural que
 *     más se usa es el ÁREA, así que Empresa y Área quedan a la vista y **Colaborador** —el
 *     recorte a UNA persona— va atrás. Es el mismo criterio con el que Colaborador quedó avanzado
 *     en ausencias y vacaciones.
 *
 * ⚠️ Y HAY UNA RAZÓN EXTRA PARA NO ESCONDER EL ÁREA EN ASIGNACIONES: con una empresa elegida en el
 * sidebar, el campo Empresa no se arma. Si Área también fuera avanzada, la fila superior del panel
 * quedaría **sin un solo control a la vista** y el usuario tendría que abrir "Más filtros" para
 * encontrar cualquier cosa — que es exactamente lo que la regla del patrón prohíbe.
 *
 * Sin estado ni efectos: reciben valores y setters, devuelven la descripción de los controles. El
 * reset de página lo dispara `onFiltroChange` en cada onChange (invariante 4 del bloque B).
 */
export const ESTADO_ITEM_OPCIONES: OpcionFiltro[] =
  Object.entries(ESTADO_ITEM_LABEL).map(([value, label]) => ({ value, label }))

export interface ArgsCamposItems {
  empresaActivaId: string | null
  empresas: Empresa[]
  empresaFiltro: string
  /** Cambiar de empresa limpia el área: un área de otra empresa deja el listado en cero. */
  cambiarEmpresa: (v: string) => void
  estadoFiltro: string
  setEstadoFiltro: (v: string) => void
  areas: Area[]
  areaFiltro: string
  setAreaFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCamposItems(a: ArgsCamposItems): FiltroCampo[] {
  const empresaId = a.empresaActivaId || a.empresaFiltro
  return [
    ...(!a.empresaActivaId && a.empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: a.empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { a.cambiarEmpresa(v); a.onFiltroChange() },
      opciones: a.empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    { tipo: "select" as const, label: "Estado", value: a.estadoFiltro, opcionTodos: "Todos los estados",
      onChange: (v: string) => { a.setEstadoFiltro(v); a.onFiltroChange() }, opciones: ESTADO_ITEM_OPCIONES },
    ...(a.areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: a.areaFiltro, opcionTodos: "Todas las áreas", avanzado: true,
      onChange: (v: string) => { a.setAreaFiltro(v); a.onFiltroChange() },
      opciones: a.areas.map((ar) => ({ value: ar.id, label: etiquetaArea(ar, a.empresas, Boolean(empresaId)) })) }] : []),
  ]
}

export interface ArgsCamposAsignaciones {
  empresaActivaId: string | null
  empresas: Empresa[]
  empresaFiltro: string
  cambiarEmpresa: (v: string) => void
  areas: Area[]
  areaFiltro: string
  setAreaFiltro: (v: string) => void
  empleados: EmpleadoSeleccionable[]
  empleadoFiltro: string
  setEmpleadoFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCamposAsignaciones(a: ArgsCamposAsignaciones): FiltroCampo[] {
  const empresaId = a.empresaActivaId || a.empresaFiltro
  return [
    ...(!a.empresaActivaId && a.empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: a.empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { a.cambiarEmpresa(v); a.onFiltroChange() },
      opciones: a.empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    ...(a.areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: a.areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { a.setAreaFiltro(v); a.onFiltroChange() },
      opciones: a.areas.map((ar) => ({ value: ar.id, label: etiquetaArea(ar, a.empresas, Boolean(empresaId)) })) }] : []),
    ...(a.empleados.length > 0 ? [{ tipo: "select" as const, label: "Colaborador", value: a.empleadoFiltro, opcionTodos: "Todos los colaboradores", avanzado: true,
      onChange: (v: string) => { a.setEmpleadoFiltro(v); a.onFiltroChange() },
      opciones: a.empleados.map((e) => ({ value: e.id, label: `${e.apellido}, ${e.nombre}` })) }] : []),
  ]
}
