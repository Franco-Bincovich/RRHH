import type { ObjetivosFiltros } from "@/services/objetivos"
import type { TipoObjetivo } from "@/types/objetivo"

/** Lo que el usuario eligió en pantalla. Strings vacíos = filtro no puesto. */
export interface ValoresFiltroObjetivos {
  mostrarEmpresa: boolean
  empresaFiltro: string
  estadoFiltro: string
  prioridadFiltro: string
  responsableFiltro: string
  tipoFiltro: TipoObjetivo | ""
}

/**
 * Los valores de pantalla → el objeto de filtros que viaja al listado Y al export.
 *
 * 🔴 ARCHIVO PROPIO Y FUNCIÓN PURA A PROPÓSITO, aunque sólo la llame `useFiltrosObjetivos`. Es el
 * ÚNICO punto donde un valor elegido puede quedarse sin llegar a la red, y adentro del hook no
 * hay forma de afirmarlo sin DOM. Se verificó por mutación: borrarle el `tipo` dejaba el selector
 * de vista SIN NINGÚN efecto y las 153 aserciones del módulo seguían en verde. Acá se afirma sola
 * (`_filtrosObjetivos.test.ts`). Mismo criterio que `_camposObjetivos.ts`, que salió del hook por
 * la misma razón: lo único ejercitable sin DOM se saca del hook.
 *
 * ⚠️ El `|| undefined` de cada campo NO es cosmético: `""` viajaría como `?estado=` y el backend
 * lo leería como un filtro puesto con valor vacío. En `tipo` sería peor todavía —es un `Literal`
 * cerrado, así que responde 422— y por eso "Todas" es `""` acá y DESAPARECE del objeto en vez de
 * viajar vacío.
 *
 * ⚠️ `empresaIdOverride` es el único con una condición además del vacío: sólo se manda en modo
 * consolidado. Con una empresa activa en el sidebar, ese header ya lo pone `apiFetch` y pisarlo
 * desde acá sería que el filtro de pantalla le gane al selector global.
 */
export function armarFiltros(v: ValoresFiltroObjetivos): ObjetivosFiltros {
  return {
    empresaIdOverride: v.mostrarEmpresa && v.empresaFiltro ? v.empresaFiltro : undefined,
    estado: v.estadoFiltro || undefined,
    responsableId: v.responsableFiltro || undefined,
    prioridad: v.prioridadFiltro || undefined,
    tipo: v.tipoFiltro || undefined,
  }
}
