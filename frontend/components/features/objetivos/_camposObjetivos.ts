import type { FiltroCampo, OpcionFiltro } from "@/components/ui/FiltersBar"
import type { Empresa } from "@/types/empresa"
import type { UserItem } from "@/types/objetivo"

/**
 * Armado del array de <FiltersBar> para /objetivos. **Reemplaza a `ObjetivosFiltros.tsx`**, que
 * era una barra propia de cuatro `<Select>` sueltos. Su propio encabezado decía que no se había
 * migrado a `FiltersBar` "a propósito: eso es un rediseño del filtro, no una división" — este es
 * ese rediseño.
 *
 * Aparte de la página por lo mismo que en el resto del bloque: **es lo único que un test puede
 * ejercitar sin DOM**, así que los chips se prueban contra el cableado real.
 *
 * 🔴 QUÉ QUEDA DETRÁS DE "MÁS FILTROS" Y POR QUÉ SÓLO RESPONSABLE. La pregunta diaria de un
 * tablero es **qué hay que hacer y con qué urgencia**, así que Empresa, Estado y Prioridad quedan
 * a la vista — son los dos ejes de triage más el alcance. **Responsable** es el recorte a UNA
 * persona ("¿qué tengo yo?"), el mismo criterio con el que Colaborador quedó avanzado en
 * ausencias, vacaciones e inventario.
 *
 * 🔴 EL ESTADO SON TRES VALORES, NO UN PORCENTAJE (§7): por hacer · haciendo · terminado. Ninguna
 * opción de este select puede insinuar una fracción de avance, porque ese dato no existe.
 *
 * ⚠️ NO HAY FILTRO POR ÁREA, y no es un olvido: `objetivos.responsable_id` es FK a `users`, no a
 * `empleados`, y los operadores de Capital Humano no tienen área. Está declarado como decisión de
 * producto en CLAUDE.md, no como deuda.
 *
 * Sin estado ni efectos: recibe valores y setters. El reset de página lo dispararía
 * `onFiltroChange`, que acá no hace falta porque **este listado no pagina** (el backend devuelve
 * el árbol entero) — se recibe igual para no divergir del molde y para el día que pagine.
 */
export const ESTADO_OPCIONES: OpcionFiltro[] = [
  { value: "por_hacer", label: "Por hacer" },
  { value: "haciendo", label: "Haciendo" },
  { value: "terminado", label: "Terminado" },
]

export const PRIORIDAD_OPCIONES: OpcionFiltro[] = [
  { value: "alta", label: "Alta" },
  { value: "media", label: "Media" },
  { value: "baja", label: "Baja" },
]

export interface ArgsCamposObjetivos {
  mostrarEmpresa: boolean
  empresas: Empresa[]
  empresaFiltro: string
  setEmpresaFiltro: (v: string) => void
  estadoFiltro: string
  setEstadoFiltro: (v: string) => void
  prioridadFiltro: string
  setPrioridadFiltro: (v: string) => void
  usuarios: UserItem[]
  responsableFiltro: string
  setResponsableFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCampos(a: ArgsCamposObjetivos): FiltroCampo[] {
  return [
    ...(a.mostrarEmpresa && a.empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: a.empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { a.setEmpresaFiltro(v); a.onFiltroChange() },
      opciones: a.empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    { tipo: "select" as const, label: "Estado", value: a.estadoFiltro, opcionTodos: "Todos los estados",
      onChange: (v: string) => { a.setEstadoFiltro(v); a.onFiltroChange() }, opciones: ESTADO_OPCIONES },
    { tipo: "select" as const, label: "Prioridad", value: a.prioridadFiltro, opcionTodos: "Todas las prioridades",
      onChange: (v: string) => { a.setPrioridadFiltro(v); a.onFiltroChange() }, opciones: PRIORIDAD_OPCIONES },
    ...(a.usuarios.length > 0 ? [{ tipo: "select" as const, label: "Responsable", value: a.responsableFiltro, opcionTodos: "Todos los responsables", avanzado: true,
      onChange: (v: string) => { a.setResponsableFiltro(v); a.onFiltroChange() },
      opciones: a.usuarios.map((u) => ({ value: u.id, label: `${u.nombre} ${u.apellido}` })) }] : []),
  ]
}
