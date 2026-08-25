import type { FiltroCampo, OpcionFiltro } from "@/components/ui/FiltersBar"
import type { Area } from "@/types/area"
import type { Capacitacion } from "@/types/capacitacion"
import type { EmpleadoSeleccionable } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"

/**
 * Armado de los arrays de <FiltersBar> de las DOS pestañas de /capacitaciones (Formación). Aparte
 * de los hooks por lo mismo que en el resto del bloque: **es lo único que un test puede ejercitar
 * sin DOM**, así que los chips se prueban contra el cableado real y no contra campos inventados.
 *
 * 🔴 EL CATÁLOGO: "SOLO ACTIVOS" DEJÓ DE SER UN CHECKBOX Y PASÓ A SER UN SELECT. Los chips se
 * derivan de los `FiltroCampo`, y el patrón tiene cinco tipos de control — ninguno es un checkbox.
 * Con el tilde, ese filtro quedaba activo sin chip y sin contador: la pantalla ocultaba los cursos
 * dados de baja y la única señal era una casilla tildada fuera del panel.
 *
 * ⚠️ Y ES BINARIO, no tri-estado: el backend recibe `solo_activos: bool` con default **True**, así
 * que "sin nada elegido" significa "sólo los activos" — igual que en /clientes y /eventos. No hay
 * forma de pedir "sólo los inactivos".
 *
 * 🔴 QUÉ QUEDA DETRÁS DE "MÁS FILTROS" EN ASIGNACIONES, Y POR QUÉ ESOS DOS. La pregunta diaria es
 * **quién debe qué** ("¿quién tiene el curso obligatorio pendiente?"), así que Empresa, Área y
 * Estado quedan a la vista. **Colaborador** es el recorte a UNA persona y **Formación** el recorte
 * a UN curso: los dos son consultas puntuales, el mismo criterio con el que Colaborador quedó
 * avanzado en ausencias y vacaciones. Los cinco filtros a la vista tapaban la tabla, que es
 * justamente lo que "Más filtros" existe para evitar.
 *
 * ⚠️ EL CATÁLOGO NO ESCONDE NADA: tiene dos controles —y uno sólo existe en modo consolidado—, así
 * que con "Más filtros" la fila superior podría quedar sin ningún control a la vista.
 *
 * Sin estado ni efectos: reciben valores y setters, devuelven la descripción de los controles.
 */
export const ACTIVOS_OPCIONES: OpcionFiltro[] = [
  { value: "todos", label: "Activos e inactivos" },
]

export const ESTADO_ASIGNACION_OPCIONES: OpcionFiltro[] = [
  { value: "pendiente", label: "Pendiente" },
  { value: "en_curso", label: "En curso" },
  { value: "completado", label: "Completado" },
]

export interface ArgsCamposCatalogo {
  empresaActivaId: string | null
  empresas: Empresa[]
  empresaFiltro: string
  setEmpresaFiltro: (v: string) => void
  activosFiltro: string
  setActivosFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCamposCatalogo(a: ArgsCamposCatalogo): FiltroCampo[] {
  return [
    ...((!a.empresaActivaId && a.empresas.length > 0) || a.empresaFiltro ? [{ tipo: "select" as const, label: "Empresa", value: a.empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { a.setEmpresaFiltro(v); a.onFiltroChange() },
      opciones: a.empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    { tipo: "select" as const, label: "Estado", value: a.activosFiltro, opcionTodos: "Sólo activos",
      onChange: (v: string) => { a.setActivosFiltro(v); a.onFiltroChange() }, opciones: ACTIVOS_OPCIONES },
  ]
}

export interface ArgsCamposAsignacionesCap {
  empresaActivaId: string | null
  empresas: Empresa[]
  empresaFiltro: string
  /** Cambiar de empresa limpia área, colaborador y formación: los tres son de UNA empresa. */
  cambiarEmpresa: (v: string) => void
  areas: Area[]
  areaFiltro: string
  setAreaFiltro: (v: string) => void
  estadoFiltro: string
  setEstadoFiltro: (v: string) => void
  empleados: EmpleadoSeleccionable[]
  empleadoFiltro: string
  setEmpleadoFiltro: (v: string) => void
  capacitaciones: Capacitacion[]
  capacitacionFiltro: string
  setCapacitacionFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCamposAsignacionesCap(a: ArgsCamposAsignacionesCap): FiltroCampo[] {
  return [
    ...((!a.empresaActivaId && a.empresas.length > 0) || a.empresaFiltro ? [{ tipo: "select" as const, label: "Empresa", value: a.empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { a.cambiarEmpresa(v); a.onFiltroChange() },
      opciones: a.empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    ...((a.areas.length > 0) || a.areaFiltro ? [{ tipo: "select" as const, label: "Área", value: a.areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { a.setAreaFiltro(v); a.onFiltroChange() },
      opciones: a.areas.map((ar) => ({ value: ar.id, label: ar.nombre })) }] : []),
    { tipo: "select" as const, label: "Estado", value: a.estadoFiltro, opcionTodos: "Todos los estados",
      onChange: (v: string) => { a.setEstadoFiltro(v); a.onFiltroChange() }, opciones: ESTADO_ASIGNACION_OPCIONES },
    ...((a.empleados.length > 0) || a.empleadoFiltro ? [{ tipo: "select" as const, label: "Colaborador", value: a.empleadoFiltro, opcionTodos: "Todos los colaboradores", avanzado: true,
      onChange: (v: string) => { a.setEmpleadoFiltro(v); a.onFiltroChange() },
      opciones: a.empleados.map((e) => ({ value: e.id, label: `${e.apellido}, ${e.nombre}` })) }] : []),
    ...((a.capacitaciones.length > 0) || a.capacitacionFiltro ? [{ tipo: "select" as const, label: "Formación", value: a.capacitacionFiltro, opcionTodos: "Todas las formaciones", avanzado: true,
      onChange: (v: string) => { a.setCapacitacionFiltro(v); a.onFiltroChange() },
      opciones: a.capacitaciones.map((c) => ({ value: c.id, label: c.nombre })) }] : []),
  ]
}
