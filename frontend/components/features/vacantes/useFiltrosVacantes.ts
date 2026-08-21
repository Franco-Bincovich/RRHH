"use client"

/**
 * Estado de los filtros de vacantes + carga de las empresas que llenan su select.
 *
 * Reemplaza al estado suelto que vivía en `app/(dashboard)/vacantes/page.tsx` (dos `useState`,
 * dos setters que además reseteaban la página y un `useEffect` para las empresas). El armado de
 * los campos vive en `_camposVacantes.ts`, que es lo que un test puede ejercitar sin DOM.
 *
 * 🔴 EL FILTRO DE EMPRESA SOLO EXISTE EN MODO CONSOLIDADO. Con una empresa elegida en el sidebar,
 * el listado ya viene acotado por el header `X-Empresa-Id` y ofrecer el select sería un control
 * que no puede cambiar nada. Por eso `empresaActivaId` gobierna si el campo se arma o no
 * (`_camposVacantes.ts`) y también si el override viaja o no.
 */
import { useEffect, useState } from "react"

import { construirCampos } from "@/components/features/vacantes/_camposVacantes"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { fetchEmpresas } from "@/services/empresas"
import type { Empresa } from "@/types/empresa"

export function useFiltrosVacantes(onFiltroChange: () => void) {
  const [empresaActivaId, setEmpresaActivaId] = useState<string | null>(null)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [estadoFiltro, setEstadoFiltro] = useState("")

  useEffect(() => {
    const id = getEmpresaActivaId()
    setEmpresaActivaId(id)
    if (!id) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [])

  const campos = construirCampos({
    empresaActivaId, empresas, empresaFiltro, setEmpresaFiltro,
    estadoFiltro, setEstadoFiltro, onFiltroChange,
  })

  // El override solo viaja en consolidado: con empresa activa manda el header del sidebar.
  const empresaOverride = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined

  return { empresaActivaId, empresaOverride, estadoFiltro, campos }
}
