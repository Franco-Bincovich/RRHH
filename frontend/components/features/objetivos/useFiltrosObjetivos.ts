import { useState } from "react"

import { construirCampos } from "@/components/features/objetivos/_camposObjetivos"
import { useCatalogosObjetivos } from "@/components/features/objetivos/_catalogosObjetivos"
import { armarFiltros } from "@/components/features/objetivos/_filtrosObjetivos"
import type { TipoObjetivo } from "@/types/objetivo"

/**
 * Estado de los filtros de /objetivos: qué eligió el usuario. Molde: `useFiltrosVacaciones` — los
 * valores acá, los catálogos en `_catalogosObjetivos`, la descripción de los controles en
 * `_camposObjetivos` y el armado del objeto de filtros en `_filtrosObjetivos` (esos dos son lo
 * único ejercitable sin DOM). UN solo objeto de filtros viaja entero al listado y al export.
 *
 * Salió de `objetivos/page.tsx`, que estaba en 147/150 y no admitía el quinto filtro. El
 * movimiento fue puro: los `useState`, la carga de catálogos, el `mostrarEmpresa`, el armado de
 * `campos` y el objeto de filtros estaban los cinco en la página.
 *
 * 🔴 `tipo` NO SE ARMA COMO LOS OTROS CUATRO, aunque viaje en el mismo objeto. Los otros son
 * `string` que salen de un `<select>` de la barra de filtros; éste es LA VISTA —anual u
 * operativo—, sale de las solapas de `TipoObjetivoTabs` y por eso vive tipado como
 * `TipoObjetivo | ""`. Está acá y no en un estado suelto de la página justamente porque tiene que
 * terminar en el MISMO `ObjetivosFiltros` que el export: si la vista se quedara afuera de ese
 * objeto, el Excel saldría con los objetivos de las dos vistas mientras la pantalla muestra una.
 */

export function useFiltrosObjetivos() {
  const { empresaActivaId, empresas, usuarios, vistas } = useCatalogosObjetivos()
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [estadoFiltro, setEstadoFiltro] = useState("")
  const [prioridadFiltro, setPrioridadFiltro] = useState("")
  const [responsableFiltro, setResponsableFiltro] = useState("")
  /** "" = las dos vistas. No es un valor del vocabulario: es la AUSENCIA del filtro. */
  const [tipoFiltro, setTipoFiltro] = useState<TipoObjetivo | "">("")

  const mostrarEmpresa = !empresaActivaId

  const campos = construirCampos({
    mostrarEmpresa, empresas, empresaFiltro, setEmpresaFiltro,
    estadoFiltro, setEstadoFiltro, prioridadFiltro, setPrioridadFiltro,
    usuarios, responsableFiltro, setResponsableFiltro,
    // Vacío a propósito: este listado no pagina, así que no hay página que resetear. Se pasa
    // igual para no divergir del molde y para el día que pagine.
    onFiltroChange: () => {},
  })

  // UN solo objeto: lo consumen el listado y el export, así que no pueden divergir.
  const filtros = armarFiltros({
    mostrarEmpresa, empresaFiltro, estadoFiltro, prioridadFiltro, responsableFiltro, tipoFiltro,
  })

  return {
    mostrarEmpresa, campos, filtros, vistas, tipoFiltro, setTipoFiltro,
    /** La empresa contra la que se ejecuta un ALTA o un IMPORT (acción, no vista). */
    empresaDestino: empresaActivaId ?? (empresaFiltro || ""),
  }
}
