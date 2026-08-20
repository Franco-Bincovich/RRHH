import { useCallback, useEffect, useState } from "react"

import { fetchEmpleados, type EmpleadosFiltros } from "@/services/empleados"
import type { EmpleadoListResponse } from "@/types/empleado"

/**
 * La CARGA del listado de empleados: pedido, estados de carga/error y el `recargar` que usan el
 * panel de superiores pendientes y los modales al guardar.
 *
 * Salió de `page.tsx` al aplicarle el patrón de vacío y carga (§3): la página quedaba en 172
 * líneas contra el límite de 150. El corte deja la página con lo que la pantalla MUESTRA
 * —encabezado, filtros, tabla, pie— y acá lo que trae los datos.
 *
 * 🔴 `data` NO SE LIMPIA AL RECARGAR, y es lo que sostiene dos cosas del patrón: el subtítulo
 * conserva el conteo real mientras llega la respuesta (la pantalla no salta) y el pie de
 * paginación no se desmonta entre filtro y filtro. El precio es que durante una recarga el total
 * mostrado es el anterior por un instante — visible y correcto para el usuario, que está viendo
 * el esqueleto al lado.
 */
export function useListadoEmpleados(filtros: EmpleadosFiltros, page: number, pageSize: number) {
  const [data, setData] = useState<EmpleadoListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const recargar = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      setData(await fetchEmpleados({ page, pageSize, ...filtros }))
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, filtros])

  useEffect(() => { recargar() }, [recargar])

  return { data, loading, error, recargar, items: data?.items ?? [], total: data?.total ?? 0 }
}
