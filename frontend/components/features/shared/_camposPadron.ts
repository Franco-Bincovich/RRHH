import { etiquetaArea } from "@/components/features/shared/filtros"
import type { FiltroCampo } from "@/components/ui/FiltersBar"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"

/**
 * Los tres controles que las pantallas del PADRÓN comparten: buscar por nombre, empresa y área.
 *
 * Extraído de `useFiltrosPadron` por el mismo motivo que `_camposEmpleados` salió de
 * `useFiltrosEmpleados`: es la lista que crece con cada filtro nuevo, y dejarla adentro del hook
 * garantiza volver a pasarse del límite de 80 en el próximo.
 *
 * ⚠️ NINGUNO ES `avanzado`: son tres, y el "Más filtros" del patrón (§3) existe para cuando la
 * fila superior no da abasto. Esconder uno de tres es agregarle un click a algo que ya entraba.
 *
 * 🔴 EL ESTADO NO ES UN FILTRO ACÁ, y por eso no está en esta lista. En /empleados el estado se
 * elige; en /proximos-ingresos y /bajas el estado ES la pantalla (`preingreso` y `baja`), lo pone
 * la página en el objeto de filtros y no se puede tocar. Ofrecerlo dejaría entrar a "Próximos
 * ingresos → Estado: Baja", que es la otra pantalla con otro orden y otras columnas.
 */
export interface ArgsCamposPadron {
  search: string
  setSearch: (v: string) => void
  /** La empresa del sidebar. Con una empresa concreta elegida, el select de empresa no va. */
  empresaActivaId: string | null
  empresas: Empresa[]
  empresaFiltro: string
  setEmpresaFiltro: (v: string) => void
  areas: Area[]
  areaFiltro: string
  setAreaFiltro: (v: string) => void
  onFiltroChange: () => void
  /** Cómo se llama en el buscador lo que se está listando: "Buscar por nombre...". */
  placeholderBusqueda: string
}

export function construirCamposPadron(a: ArgsCamposPadron): FiltroCampo[] {
  return [
    { tipo: "search" as const, label: "Buscar", value: a.search, placeholder: a.placeholderBusqueda, onChange: a.setSearch },
    // El select de Empresa solo existe en modo consolidado: con una empresa elegida en el
    // sidebar sería un segundo control diciendo lo mismo, y los dos podrían discrepar.
    ...(!a.empresaActivaId && a.empresas.length > 0 ? [{ tipo: "select" as const, label: "Empresa", value: a.empresaFiltro, opcionTodos: "Todas las empresas",
      // Cambiar de empresa LIMPIA el área: un área de otra empresa deja el listado en cero sin
      // ninguna explicación a la vista. Mismo handler que /empleados.
      onChange: (v: string) => { a.setEmpresaFiltro(v); a.setAreaFiltro(""); a.onFiltroChange() },
      opciones: a.empresas.map((e) => ({ value: e.id, label: e.nombre })) }] : []),
    ...(a.areas.length > 0 ? [{ tipo: "select" as const, label: "Área", value: a.areaFiltro, opcionTodos: "Todas las áreas",
      onChange: (v: string) => { a.setAreaFiltro(v); a.onFiltroChange() },
      opciones: a.areas.map((ar) => ({ value: ar.id, label: etiquetaArea(ar, a.empresas, Boolean(a.empresaActivaId || a.empresaFiltro)) })) }] : []),
  ]
}
