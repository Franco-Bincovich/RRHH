"use client"

import { useCallback, useEffect, useState } from "react"

import { cargarEmpleados } from "@/components/features/shared/cargarEmpleados"
import { MAX_PAGE_SIZE } from "@/services/api"
import { fetchAreas } from "@/services/areas"
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
 *
 * 🔴 EL ERROR DE LOS CANDIDATOS SE DEVUELVE; EL DE LAS ÁREAS NO, y la asimetría es deliberada.
 * Los candidatos SON el contenido del modal: sin ellos no hay nada que hacer, y decir "sin
 * candidatos" cuando lo que hubo fue un fallo manda al usuario a buscar el problema en los datos.
 * Las áreas son un FILTRO opcional: si no cargan, el desplegable queda con "Todas las áreas" y el
 * modal sigue siendo usable — degradar ahí es correcto, taparlo en los candidatos no.
 */
export function useCandidatosProyecto(open: boolean, areaFiltro: string) {
  const [empleados, setEmpleados] = useState<Empleado[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(false)
  const [intento, setIntento] = useState(0)

  useEffect(() => {
    if (!open) return
    fetchAreas(undefined).then(setAreas).catch(() => setAreas([]))
  }, [open])

  useEffect(() => {
    if (!open) return
    // 🔴 `MAX_PAGE_SIZE` (100) es el TOPE del endpoint (`Query(20, ge=1, le=100)`), no una
    // preferencia: con 200 el backend responde 422 y no llega ninguna fila. Este modal mostró
    // "Sin candidatos." en producción durante meses por exactamente eso. No lo subas acá — el
    // número que manda es el `le` del router.
    void cargarEmpleados(
      { page: 1, pageSize: MAX_PAGE_SIZE, estado: "activo",
        empresaId: "todas", areaId: areaFiltro || undefined },
      { setEmpleados, setCargando, setError },
    )
  }, [open, areaFiltro, intento])

  const recargar = useCallback(() => setIntento((n) => n + 1), [])

  return { empleados, areas, cargando, error, recargar }
}
