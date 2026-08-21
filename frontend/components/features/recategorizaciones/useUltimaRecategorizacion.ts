import { useEffect, useState } from "react"

import { fetchHistorialRecategorizaciones } from "@/services/recategorizaciones"

import { ultimaFechaEfectiva } from "./_retroactiva"

/**
 * La fecha de la ÚLTIMA recategorización de una persona, para poder avisar en el momento si la
 * que se está cargando queda atrás en la cadena.
 *
 * 🔴 SE PIDE AL BACKEND Y NO SE DEDUCE DE LA PLANILLA. La planilla está PAGINADA y filtrada: si
 * el usuario está en la página 2, o con un rango de fechas puesto, la fila más reciente de esa
 * persona puede no estar en `items` — y el aviso saldría al revés justo en el caso que importa.
 * `GET /api/empleados/{id}/recategorizaciones` devuelve el historial completo de esa persona, sin
 * paginar, que es exactamente la pregunta.
 *
 * ⚠️ SU FALLA NO BLOQUEA EL FORMULARIO: si la consulta se cae, `ultima` queda en `null` y el aviso
 * no aparece. Es la degradación correcta — el alta es válida igual y el backend aplica la misma
 * regla con o sin aviso. Bloquear el guardado porque no se pudo cargar un aviso sería convertir
 * un problema de red en un problema de negocio.
 *
 * ⚠️ Se re-pide al cambiar de persona, y se limpia mientras tanto: dejar la fecha del empleado
 * anterior mostraría un aviso calculado contra la cadena equivocada.
 */
export function useUltimaRecategorizacion(empleadoId: string, activo: boolean): string | null {
  const [ultima, setUltima] = useState<string | null>(null)

  useEffect(() => {
    setUltima(null)
    if (!activo || !empleadoId) return
    let cancelado = false
    fetchHistorialRecategorizaciones(empleadoId)
      .then((items) => { if (!cancelado) setUltima(ultimaFechaEfectiva(items)) })
      .catch(() => { /* ver el ⚠️ del encabezado: sin aviso, no sin formulario */ })
    return () => { cancelado = true }
  }, [empleadoId, activo])

  return ultima
}
