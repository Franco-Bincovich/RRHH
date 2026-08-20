/**
 * Estado de los filtros de ausencias y armado del array de FiltroCampo para <FiltersBar>.
 * `onFiltroChange` se dispara en cada cambio (la página lo usa para resetear la paginación a 1).
 * El select de empleado solo aparece con empresa definida (igual que áreas).
 *
 * La CARGA de las opciones vive en `useOpcionesAusencias`: acá queda "qué está elegido" y allá
 * "qué se puede elegir". Ver el encabezado de aquel para el porqué del corte.
 */
import { useState } from "react"

import { useOpcionesAusencias } from "@/components/features/ausencias/useOpcionesAusencias"
import { etiquetaArea } from "@/components/features/shared/filtros"
import type { FiltroCampo, RangoFechas } from "@/components/ui/FiltersBar"
import type { AusenciasFiltros } from "@/services/ausencias"

export function useFiltrosAusencias(onFiltroChange: () => void) {
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [areaFiltro, setAreaFiltro] = useState("")
  const [empleadoFiltro, setEmpleadoFiltro] = useState("")
  const [tipoFiltro, setTipoFiltro] = useState("")
  const [proyectoFiltro, setProyectoFiltro] = useState("")
  const [rango, setRango] = useState<RangoFechas>({ desde: "", hasta: "" })

  const { empresaActivaId, empresas, areas, empleadosSel, tipos, proyectos } =
    useOpcionesAusencias(empresaFiltro)

  const campos: FiltroCampo[] = [
    ...(!empresaActivaId && empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { setEmpresaFiltro(v); setAreaFiltro(""); setEmpleadoFiltro(""); onFiltroChange() },
      opciones: empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    ...(areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { setAreaFiltro(v); onFiltroChange() },
      opciones: areas.map((a) => ({ value: a.id, label: etiquetaArea(a, empresas, Boolean(empresaActivaId || empresaFiltro)) })) }] : []),
    ...(empleadosSel.length > 0 ? [{ tipo: "select" as const, label: "Colaborador", value: empleadoFiltro, opcionTodos: "Todos los colaboradores",
      onChange: (v: string) => { setEmpleadoFiltro(v); onFiltroChange() },
      opciones: empleadosSel.map((e) => ({ value: e.id, label: `${e.apellido}, ${e.nombre}` })) }] : []),
    // Elegir un PADRE trae también las ausencias de sus hijos: la familia la resuelve el
    // backend (`AusenciasService.get_all`), que es el mismo punto por el que pasa el export.
    // Acá solo se etiqueta el subtipo con su padre para que la lista se lea en dos niveles.
    ...(tipos.length > 0 ? [{ tipo: "select" as const, label: "Tipo", value: tipoFiltro, opcionTodos: "Todos los tipos",
      onChange: (v: string) => { setTipoFiltro(v); onFiltroChange() },
      opciones: tipos.map((t) => ({ value: t.id, label: t.padre_nombre ? `${t.padre_nombre} › ${t.nombre}` : t.nombre })) }] : []),
    { tipo: "daterange" as const, label: "Período",
      value: rango,
      onChange: (v: RangoFechas) => { setRango(v); onFiltroChange() } },
    ...(proyectos.length > 0 ? [{ tipo: "select" as const, label: "Proyecto", value: proyectoFiltro, opcionTodos: "Todos los proyectos",
      onChange: (v: string) => { setProyectoFiltro(v); onFiltroChange() },
      opciones: proyectos.map((p) => ({ value: p.id, label: p.nombre })) }] : []),
  ]

  // Un solo objeto de filtros: lo consumen el listado y el export, así que no pueden divergir.
  const filtros: AusenciasFiltros = {
    empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined,
    areaId: areaFiltro || undefined,
    tipoId: tipoFiltro || undefined,
    empleadoId: empleadoFiltro || undefined,
    fechaDesde: rango.desde || undefined,
    fechaHasta: rango.hasta || undefined,
    proyectoId: proyectoFiltro || undefined,
  }
  return { empresaActivaId, filtros, campos }
}
