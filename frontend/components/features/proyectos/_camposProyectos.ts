import { etiquetaArea } from "@/components/features/shared/filtros"
import type { FiltroCampo } from "@/components/ui/FiltersBar"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"
import type { ProyectoEstado } from "@/types/proyecto"

/**
 * Armado del array de <FiltersBar> para /proyectos. Extraído de `useFiltrosProyectos.ts` por lo
 * mismo que en el resto del bloque: **es lo único que un test puede ejercitar sin DOM**, así que
 * los chips se prueban contra el cableado real y no contra campos inventados.
 *
 * 🔴 QUÉ QUEDA DETRÁS DE "MÁS FILTROS" Y POR QUÉ SÓLO ÁREA. Quién es avanzado lo decide cada
 * pantalla, nunca la posición del campo. La pregunta diaria acá es del ESTADO ("¿cuáles están
 * activos?", "¿cuáles quedaron pausados?") y del alcance (la empresa dueña), así que esos dos
 * quedan a la vista. **Área** es el recorte a OTRA entidad: no es una columna de `proyectos` sino
 * un cruce —"proyectos donde trabaja al menos alguien de esa área"— que el backend resuelve por
 * las asignaciones. Mismo criterio que en /empleados, /vacaciones y /ausencias.
 *
 * ⚠️ Y ESE CRUCE TIENE DEFINICIONES QUE HAY QUE CONOCER ANTES DE TOCARLO (están en
 * `repositories/_scope_filtros.py`): cuenta asignaciones activas E inactivas, y un proyecto sin
 * nadie asignado NO aparece bajo ninguna área — es la definición, no un bug.
 *
 * Sin estado ni efectos: recibe valores y setters, devuelve la descripción de los controles. El
 * reset de página lo dispara `onFiltroChange` en cada onChange (invariante 4 del bloque B).
 */
export const ESTADO_OPCIONES: { value: ProyectoEstado; label: string }[] = [
  { value: "activo", label: "Activo" },
  { value: "pausado", label: "Pausado" },
  { value: "cerrado", label: "Cerrado" },
  { value: "cancelado", label: "Cancelado" },
]

export interface ArgsCamposProyectos {
  empresaActivaId: string | null
  empresas: Empresa[]
  empresaFiltro: string
  setEmpresaFiltro: (v: string) => void
  estadoFiltro: string
  setEstadoFiltro: (v: string) => void
  areas: Area[]
  areaFiltro: string
  setAreaFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCampos(a: ArgsCamposProyectos): FiltroCampo[] {
  const empresaId = a.empresaActivaId || a.empresaFiltro
  return [
    ...(!a.empresaActivaId && a.empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: a.empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { a.setEmpresaFiltro(v); a.setAreaFiltro(""); a.onFiltroChange() },
      opciones: a.empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    { tipo: "select" as const, label: "Estado", value: a.estadoFiltro, opcionTodos: "Todos los estados",
      onChange: (v: string) => { a.setEstadoFiltro(v); a.onFiltroChange() }, opciones: ESTADO_OPCIONES },
    ...(a.areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: a.areaFiltro, opcionTodos: "Todas las áreas", avanzado: true,
      onChange: (v: string) => { a.setAreaFiltro(v); a.onFiltroChange() },
      opciones: a.areas.map((ar) => ({ value: ar.id, label: etiquetaArea(ar, a.empresas, Boolean(empresaId)) })) }] : []),
  ]
}
