"use client"

import { useCallback, useEffect, useState } from "react"

import { fetchAreas } from "@/services/areas"
import { fetchMapaTalento, fetchPlanesCarrera } from "@/services/sucesion"
import type { Area } from "@/types/area"
import type { EmpleadoMapa, PlanCarrera } from "@/types/sucesion"

// Datos base de la pantalla de sucesión: mapa 9-box, planes de carrera y áreas. Las tres cargas
// se disparan juntas una sola vez al montar, igual que antes de la división.
// `planes`/`setPlanes` se exponen porque el panel de detalle refleja hitos y readiness en la
// lista sin recargarla; `recargarPlanes` lo usa el alta de plan (esa sí recarga del backend).
// `selectedArea` vive acá porque lo comparten el filtro del mapa y el modal de análisis.
export function useSucesionData() {
  const [rawEmpleados, setRawEmpleados]   = useState<EmpleadoMapa[]>([])
  const [planes, setPlanes]               = useState<PlanCarrera[]>([])
  const [areas, setAreas]                 = useState<Area[]>([])
  const [selectedArea, setSelectedArea]   = useState<string>("")
  const [loadingMapa, setLoadingMapa]     = useState(true)
  const [loadingPlanes, setLoadingPlanes] = useState(true)
  const [errorMapa, setErrorMapa]         = useState<string | null>(null)
  const [errorPlanes, setErrorPlanes]     = useState<string | null>(null)

  // Las dos recargas salen del efecto para que el `ErrorState` de cada tab pueda volver a
  // disparar SU carga: reintentar el mapa no tiene por qué recargar los planes, que quizás ya
  // llegaron bien. El `setError(null)` va adentro, si no el reintento arranca mostrando el error
  // anterior hasta que la respuesta vuelva.
  const recargarMapa = useCallback(() => {
    setLoadingMapa(true)
    setErrorMapa(null)
    fetchMapaTalento()
      .then(setRawEmpleados)
      .catch(() => setErrorMapa("No se pudo cargar el mapa de talento."))
      .finally(() => setLoadingMapa(false))
  }, [])

  const recargarPlanes = useCallback(() => {
    setLoadingPlanes(true)
    setErrorPlanes(null)
    fetchPlanesCarrera()
      .then(setPlanes)
      .catch(() => setErrorPlanes("No se pudo cargar los planes de carrera."))
      .finally(() => setLoadingPlanes(false))
  }, [])

  useEffect(() => {
    recargarMapa()
    recargarPlanes()

    fetchAreas().then(setAreas).catch(() => setAreas([]))
  }, [recargarMapa, recargarPlanes])

  return {
    rawEmpleados, planes, setPlanes, areas,
    selectedArea, setSelectedArea,
    loadingMapa, loadingPlanes, errorMapa, errorPlanes,
    recargarMapa, recargarPlanes,
  }
}
