import { useState } from "react"
import { toast } from "sonner"

import { deletePerfil, updatePerfil } from "@/services/perfilesPuesto"
import type { PerfilPuesto } from "@/types/perfilPuesto"

/**
 * Las dos escrituras que NO pasan por el formulario: dar de baja y reactivar.
 *
 * Salió de la página, que quedaba en 167 líneas contra el límite de 150 de un componente. El
 * corte no es por tamaño: la página quedó con lo que la pantalla MUESTRA y acá está el par de
 * acciones que la MODIFICAN sin abrir el modal. Las dos comparten el mismo `onCambio` —recargar
 * el listado— y el mismo criterio de error.
 *
 * 🔴 LA BAJA Y LA REACTIVACIÓN SON LA MISMA OPERACIÓN EN LOS DOS SENTIDOS, y por eso viven
 * juntas: `deletePerfil` es un `activo=False` (baja LÓGICA, el 204 no lo dice) y reactivar es el
 * `activo=True` por el PUT. No hay borrado físico en ningún camino —`vacantes.perfil_puesto_id`
 * es `ON DELETE SET NULL` y un DELETE real le arrancaría en silencio la trazabilidad a toda
 * vacante creada desde ese perfil—, así que la pantalla nunca ofrece una acción irreversible.
 *
 * ⚠️ SOLO LA BAJA PIDE CONFIRMACIÓN. Reactivar no abre ningún diálogo: es la operación que
 * DESHACE, y pedir confirmación para deshacer convierte el arrepentimiento en un trámite. Es el
 * mismo criterio con el que `ActivarEmpleadoButton` no lleva `ConfirmDialog` y la efectivización
 * de una baja sí — lo que decide no es la importancia, es la reversibilidad.
 */
export function useAccionesPerfil(onCambio: () => void) {
  const [aBaja, setABaja] = useState<PerfilPuesto | null>(null)
  const [bajando, setBajando] = useState(false)

  async function confirmarBaja() {
    if (!aBaja) return
    setBajando(true)
    try {
      await deletePerfil(aBaja.id)
      setABaja(null)
      onCambio()
    } catch {
      toast.error("No se pudo dar de baja el perfil. Intentá de nuevo.")
    } finally {
      setBajando(false)
    }
  }

  async function reactivar(perfil: PerfilPuesto) {
    try {
      await updatePerfil(perfil.id, { activo: true })
      onCambio()
    } catch {
      toast.error("No se pudo reactivar el perfil. Intentá de nuevo.")
    }
  }

  return { aBaja, setABaja, bajando, confirmarBaja, reactivar }
}
