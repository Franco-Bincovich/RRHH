"use client"

import { useEffect, useState } from "react"

import { fetchAreas } from "@/services/areas"
import { fetchEmpleados } from "@/services/empleados"
import type { Area } from "@/types/area"
import type { Empleado } from "@/types/empleado"

/**
 * Los CANDIDATOS a asignar y las áreas para filtrarlos. Solo trae datos.
 *
 * Extraído de `useAsignarEmpleados`, que pasó el límite de 80 líneas de un hook al sumarle el
 * alta por área. Mismo corte que `useOpcionesAusencias`: acá "qué se puede elegir", allá "qué
 * está elegido y qué se hace con eso".
 *
 * ⚠️ Los candidatos se piden de TODAS las empresas (`empresaId: "todas"`) a propósito: un
 * proyecto puede tener gente de otra empresa del grupo, y por eso `proyecto_asignaciones` guarda
 * `empleado_empresa_id`. El área acota server-side.
 */
export function useCandidatosProyecto(open: boolean, areaFiltro: string) {
  const [empleados, setEmpleados] = useState<Empleado[]>([])
  const [areas, setAreas] = useState<Area[]>([])

  useEffect(() => {
    if (!open) return
    fetchAreas(undefined).then(setAreas).catch(() => setAreas([]))
  }, [open])

  useEffect(() => {
    if (!open) return
    fetchEmpleados({ page: 1, pageSize: 200, estado: "activo", empresaId: "todas", areaId: areaFiltro || undefined })
      .then((r) => setEmpleados(r.items ?? [])).catch(() => setEmpleados([]))
  }, [open, areaFiltro])

  return { empleados, areas }
}
