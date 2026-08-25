import type { FiltroCampo } from "@/components/ui/FiltersBar"
import type { Empresa } from "@/types/empresa"

import { ESTADO_LABEL } from "./_grillaVacantes"

/**
 * Armado del array de <FiltersBar> para /vacantes. Reemplaza a `VacantesFiltros.tsx`, que dibujaba
 * dos `<Select>` sueltos arriba de la tabla: los mismos dos controles, ahora adentro del panel del
 * patrón y con su fila de chips. Aparte de la página por lo mismo que en las otras pantallas del
 * bloque: **es lo único que un test puede ejercitar sin DOM**.
 *
 * 🔴 ACÁ NO HAY NINGÚN FILTRO AVANZADO, Y ESO ES UNA DECISIÓN. La pantalla tiene DOS filtros —y
 * uno de ellos, Empresa, solo existe en modo consolidado, así que la mitad del tiempo hay UNO—.
 * La regla del patrón ("un 'Más filtros' para el resto") existe para que una fila de siete
 * controles no tape la tabla; con dos, esconder uno atrás de un botón deja la mitad de la
 * pantalla inalcanzable a cambio de nada.
 *
 * ⚠️ LAS ETIQUETAS DE ESTADO SALEN DE `ESTADO_LABEL`, el MISMO mapa que pinta el badge de cada
 * fila y que copia los textos del export. Escribirlas de nuevo acá daría dos catálogos del mismo
 * dato: el chip podría decir "En proceso" y la fila "en_proceso" sin que nada falle.
 *
 * Sin estado ni efectos: recibe valores y setters, devuelve la descripción de los controles. El
 * reset de página lo dispara `onFiltroChange` en cada onChange (invariante 4 del bloque B).
 */
export const ESTADO_OPCIONES = (Object.keys(ESTADO_LABEL) as (keyof typeof ESTADO_LABEL)[])
  .map((value) => ({ value, label: ESTADO_LABEL[value] }))

export interface ArgsCamposVacantes {
  /** El del sidebar. Con una empresa elegida, el filtro de empresa no se ofrece. */
  empresaActivaId: string | null
  empresas: Empresa[]
  empresaFiltro: string
  setEmpresaFiltro: (v: string) => void
  estadoFiltro: string
  setEstadoFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCampos(a: ArgsCamposVacantes): FiltroCampo[] {
  return [
    ...((!a.empresaActivaId && a.empresas.length > 0) || a.empresaFiltro ? [{ tipo: "select" as const, label: "Empresa", value: a.empresaFiltro, opcionTodos: "Todas las empresas",
      onChange: (v: string) => { a.setEmpresaFiltro(v); a.onFiltroChange() },
      opciones: a.empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    { tipo: "select" as const, label: "Estado", value: a.estadoFiltro, opcionTodos: "Todos los estados",
      onChange: (v: string) => { a.setEstadoFiltro(v); a.onFiltroChange() }, opciones: ESTADO_OPCIONES },
  ]
}
