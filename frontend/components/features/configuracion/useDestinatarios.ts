"use client"

import { useEffect, useState } from "react"

import { fetchEmpleados } from "@/services/empleados"
import type { Empleado } from "@/types/empleado"

/**
 * A quiénes se les puede mandar un mail. Solo trae datos; la selección vive en
 * `useEnvioPlantilla`. Mismo corte que `useCandidatosProyecto` / `useOpcionesAusencias`.
 *
 * ⚠️ NO pasa `empresaId`, al revés que `useCandidatosProyecto`, y la diferencia es deliberada:
 * allá un proyecto puede tener gente de otra empresa del grupo, acá el mail sale con la plantilla
 * de UNA empresa y se registra bajo esa empresa. Sin el parámetro, `apiFetch` manda la del
 * sidebar — que es exactamente la que el backend va a usar para resolver la plantilla.
 *
 * `habilitado` en false no pide nada: es lo que impide que el modal dispare un request antes de
 * saber si hay empresa elegida (ver el tri-estado de `sinEmpresa` en `useEnvioPlantilla`).
 */
export function useDestinatarios(open: boolean, habilitado: boolean) {
  const [empleados, setEmpleados] = useState<Empleado[]>([])
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    if (!open || !habilitado) return
    setCargando(true)
    // Solo activos: mandarle la plantilla de bienvenida a alguien dado de baja es el error que
    // no se puede deshacer. El backend igual registra el fallo si no tiene email cargado.
    fetchEmpleados({ page: 1, pageSize: 200, estado: "activo" })
      .then((r) => setEmpleados(r.items ?? []))
      .catch(() => setEmpleados([]))
      .finally(() => setCargando(false))
  }, [open, habilitado])

  return { empleados, cargando }
}
