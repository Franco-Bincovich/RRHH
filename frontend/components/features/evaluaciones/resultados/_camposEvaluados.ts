import type { FiltroCampo } from "@/components/ui/FiltersBar"
import type { Proyecto } from "@/types/proyecto"

/**
 * Armado del array de <FiltersBar> del listado de evaluados. Salió de
 * `useFiltrosEvaluadosResultados` al migrar la pantalla al patrón del bloque B: es **lo único que
 * un test puede ejercitar sin DOM** —los chips se prueban contra el cableado real y no contra
 * campos inventados— y además ese hook pasaba de las 80 líneas que puede tener.
 *
 * 🔴 PROYECTO ES EL ÚNICO FILTRO AVANZADO, y el criterio no es la posición: la pregunta diaria acá
 * es del RESULTADO —"¿quién quedó sin nota?", "¿cómo salió cada sector?", "¿los líderes o los
 * generales?"— así que Sector, Perfil y Nota final quedan a la vista. **Proyecto** cruza con otro
 * módulo (sale de las asignaciones de proyectos, no del lote), que es el mismo criterio con el que
 * quedó avanzado en /empleados, /vacaciones y /ausencias.
 *
 * 🔴 ACÁ NO SE HABLA DE "CICLOS". El sistema **no corre evaluaciones: importa resultados**
 * calculados afuera (`docs/SISTEMA-DE-DISENO.md` §7). Ninguna etiqueta de esta barra puede
 * insinuar un proceso con instancias, vencimientos ni recordatorios, porque nada de eso existe.
 */
export const PERFIL_OPCIONES = [
  { value: "lider", label: "Líder" },
  { value: "general", label: "General" },
]

export const NOTA_OPCIONES = [
  { value: "si", label: "Con nota" },
  { value: "no", label: "Sin nota" },
]

export interface ArgsCamposEvaluados {
  /** Los sectores del LOTE ENTERO, no los de la página: vienen en la respuesta del backend. */
  sectores: string[]
  sector: string
  setSector: (v: string) => void
  perfil: string
  setPerfil: (v: string) => void
  conNota: string
  setConNota: (v: string) => void
  proyectos: Proyecto[]
  proyecto: string
  setProyecto: (v: string) => void
  onFiltroChange: () => void
}

export function construirCamposEvaluados(a: ArgsCamposEvaluados): FiltroCampo[] {
  /** Un solo lugar donde "setear un filtro" implica volver a la página 1. */
  const cambiar = (set: (v: string) => void) => (v: string) => { set(v); a.onFiltroChange() }
  return [
    { tipo: "select" as const, label: "Sector", value: a.sector, onChange: cambiar(a.setSector),
      opcionTodos: "Todos los sectores", opciones: a.sectores.map((s) => ({ value: s, label: s })) },
    { tipo: "select" as const, label: "Perfil", value: a.perfil, onChange: cambiar(a.setPerfil),
      opcionTodos: "Los dos perfiles", opciones: PERFIL_OPCIONES },
    { tipo: "select" as const, label: "Nota final", value: a.conNota, onChange: cambiar(a.setConNota),
      opcionTodos: "Con y sin nota", opciones: NOTA_OPCIONES },
    ...((a.proyectos.length > 0) || a.proyecto ? [{ tipo: "select" as const, label: "Proyecto", value: a.proyecto,
      onChange: cambiar(a.setProyecto), opcionTodos: "Todos los proyectos", avanzado: true,
      opciones: a.proyectos.map((p) => ({ value: p.id, label: p.nombre })) }] : []),
  ]
}
