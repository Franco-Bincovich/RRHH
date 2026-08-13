"use client"

import { useCallback, useEffect, useState } from "react"

import { cargarEmpleados } from "@/components/features/shared/cargarEmpleados"
import { MAX_PAGE_SIZE } from "@/services/api"
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
 *
 * 🔴 DEVUELVE TRES ESTADOS, NO DOS: cargando · error · lista (que puede estar vacía de verdad).
 * Antes el `.catch` hacía `setEmpleados([])` y descartaba el error, así que un fallo de red, un
 * 401, un 403 y un 422 salían todos por la pantalla como "no hay empleados activos" — la UI
 * afirmando un hecho sobre los datos cuando lo que hubo fue un error. Fue exactamente así como
 * el `page_size=200` de acá abajo llegó a producción y se vio como una base vacía teniendo 31
 * empleados activos.
 */
export function useDestinatarios(open: boolean, habilitado: boolean) {
  const [empleados, setEmpleados] = useState<Empleado[]>([])
  // 🔴 CUÁNTOS HAY DE VERDAD, que puede ser MÁS de los que se traen. Este modal sigue pidiendo
  // una página de 100 —es multi-selección y la búsqueda server-side rompería la selección: ver
  // `useSeleccionEmpleados`— así que con 400 activos se están mostrando 100. Lo que NO puede
  // seguir pasando es que no se diga: una lista recortada en silencio se lee como la lista
  // entera, y acá el desenlace es un comunicado que no le llega a 300 personas.
  const [total, setTotal] = useState(0)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(false)
  // Cambiarlo re-dispara el efecto: es lo que hace que "Reintentar" sea una línea y no un
  // segundo camino de carga que pueda divergir del primero.
  const [intento, setIntento] = useState(0)

  useEffect(() => {
    if (!open || !habilitado) return
    // 🔴 `MAX_PAGE_SIZE` (100) es el TOPE del endpoint (`Query(20, ge=1, le=100)`), no una
    // preferencia: con 200 el backend responde 422 y no llega ninguna fila. No lo subas acá —
    // el número que manda es el `le` del router. Solo activos: mandarle la plantilla de
    // bienvenida a alguien dado de baja es el error que no se puede deshacer.
    void cargarEmpleados(
      { page: 1, pageSize: MAX_PAGE_SIZE, estado: "activo" },
      { setEmpleados, setCargando, setError, setTotal },
    )
  }, [open, habilitado, intento])

  const recargar = useCallback(() => setIntento((n) => n + 1), [])

  return { empleados, total, cargando, error, recargar }
}
