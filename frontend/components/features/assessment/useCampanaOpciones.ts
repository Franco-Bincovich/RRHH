"use client"

import { useEffect, useState } from "react"

import { fetchAreas } from "@/services/areas"
import { fetchEmpresas } from "@/services/empresas"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"

/**
 * QUÉ SE PUEDE ELEGIR en el alta de una campaña: las empresas activas y las áreas de la empresa
 * elegida. La otra mitad —qué está elegido, y el submit— se queda en `CampanaModal`.
 *
 * 🔴 Salió del modal porque ese archivo estaba en 202 líneas contra un límite de 150 (deuda ya
 * anotada en CLAUDE.md) y el patrón le sumaba unas cuantas más. El corte es el mismo que en el
 * resto del repo: "qué se puede elegir" es un hook, "qué está elegido" es estado del componente.
 *
 * ⚠️ Las empresas se cargan SÓLO con el sidebar en consolidado: con una empresa concreta activa
 * ya está decidida, y el selector no se muestra. Los errores de las dos cargas se tragan a
 * propósito —caen en lista vacía— porque son catálogos de apoyo: lo que el usuario tiene que ver
 * si algo falla es el error del submit, no dos carteles en un formulario que todavía no mandó.
 */
export function useCampanaOpciones(
  open: boolean,
  empresaActivaId: string | null,
  empresaId: string,
  setEmpresaId: (id: string) => void,
  setAreaId: (id: string) => void,
) {
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [areas, setAreas] = useState<Area[]>([])

  useEffect(() => {
    if (!open) return
    // Solo cargar empresas cuando topbar = "Todas"
    if (!empresaActivaId) {
      fetchEmpresas()
        .then((res) => {
          const activas = res.items.filter((e) => e.activa)
          setEmpresas(activas)
          if (activas.length > 0 && !empresaId) setEmpresaId(activas[0].id)
        })
        .catch(() => {})
    }
    // Cargar áreas filtradas por empresa activa (apiFetch envía X-Empresa-Id automáticamente)
    fetchAreas()
      .then(setAreas)
      .catch(() => setAreas([]))
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  // Cuando cambia la empresa seleccionada, recargar las áreas de esa empresa
  useEffect(() => {
    if (!open || empresaActivaId) return
    if (!empresaId) { setAreas([]); return }
    fetchAreas(empresaId)
      .then(setAreas)
      .catch(() => setAreas([]))
    setAreaId("")
  }, [empresaId]) // eslint-disable-line react-hooks/exhaustive-deps

  return { empresas, areas }
}
