import { useEffect, useState } from "react"

import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { fetchCamposObjetivo, fetchUsuariosActivos } from "@/services/objetivos"
import type { Empresa } from "@/types/empresa"
import type { TipoObjetivo, UserItem } from "@/types/objetivo"

/** Una de las dos vistas del módulo, con la etiqueta que le pone el backend. */
export type OpcionVista = { value: TipoObjetivo; label: string }

/**
 * Los catálogos que alimentan los filtros de /objetivos. Molde: `useOpcionesVacaciones`.
 *
 * Aparte de `useFiltrosObjetivos` por lo mismo que allá: el hook de filtros quedaba en 80/80 al
 * sumar el catálogo de vistas, y el próximo filtro lo pasaba. Acá va lo que se PIDE; allá, lo que
 * el usuario ELIGE.
 *
 * 🔴 EL VOCABULARIO DE LAS VISTAS SE PIDE ACÁ Y NO ADENTRO DEL SELECTOR, y no es orden: es lo que
 * deja a `TipoObjetivoTabs` presentacional y por lo tanto verificable sin jsdom. Con el fetch
 * adentro del componente, vitest (`environment: "node"`) no corre su `useEffect` y el único
 * estado que un test podría ver es el de carga — o sea que las dos solapas que importan no las
 * miraría nadie. Es el caso #4 de "un test solo prueba lo que el fake puede desmentir".
 *
 * ⚠️ Los tres `.catch(() => {})` son deliberados y NO tapan un error del listado: son catálogos
 * de SELECTORES. Si uno no llega, su control no se dibuja (`construirCampos` y el selector de
 * vista omiten los que vienen vacíos) y la pantalla sigue mostrando los objetivos. El error del
 * listado sí se muestra, y lo maneja la página.
 */
export function useCatalogosObjetivos() {
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [usuarios, setUsuarios] = useState<UserItem[]>([])
  const [vistas, setVistas] = useState<OpcionVista[]>([])

  useEffect(() => {
    if (!empresaActivaId) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
    fetchUsuariosActivos().then((r) => setUsuarios(r.items)).catch(() => {})
    fetchCamposObjetivo().then((r) => setVistas(r.tipos)).catch(() => {})
  }, [empresaActivaId])

  return { empresaActivaId, empresas, usuarios, vistas }
}
