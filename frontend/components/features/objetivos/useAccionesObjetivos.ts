"use client"

import { useState } from "react"
import { toast } from "sonner"

import { useConfirmacion } from "@/components/features/shared/useConfirmacion"
import { cambiarEstadoObjetivo, deleteObjetivo } from "@/services/objetivos"
import type { EstadoObjetivo, Objetivo } from "@/types/objetivo"

/**
 * Las dos escrituras del tablero que NO pasan por el formulario: mover una tarjeta de columna y
 * borrar un objetivo.
 *
 * Salió de `app/(dashboard)/objetivos/page.tsx`, que quedó en 161 contra el límite de 150 al
 * sumarle la confirmación del borrado. Molde exacto: `useAccionesPerfil`, que existe por lo
 * mismo (su página quedaba en 167). El corte tampoco es por tamaño: la página quedó con lo que
 * la pantalla MUESTRA y acá está lo que la MODIFICA sin abrir el modal.
 *
 * 🔴 SOLO EL BORRADO PIDE CONFIRMACIÓN, Y MOVER NO. Lo que decide no es la importancia sino la
 * REVERSIBILIDAD: mover una tarjeta al lugar equivocado se arregla moviéndola de vuelta, y pedir
 * confirmación para algo que se deshace con un click convierte el arrepentimiento en un trámite.
 * Es el mismo criterio con el que `ActivarEmpleadoButton` no lleva diálogo y la efectivización de
 * una baja sí, y el que `useAccionesPerfil` deja escrito para reactivar.
 *
 * 🔴 EL BORRADO DE UN OBJETIVO ES EL CASO MÁS CARO DE TODA LA PANTALLA, y por eso su diálogo
 * cuenta los hijos. La FK `parent_id` es ON DELETE CASCADE (migración 095): borrar un padre se
 * lleva los subobjetivos, y hasta el 24/8/2026 eso ocurría con UN CLICK y sin nombrar lo que se
 * llevaba puesto. En esa ventana desapareció un objetivo real de Karstec. El texto lo dice —ver
 * `confirmarEliminarObjetivo`— y desde esa misma fecha el backend además lo audita.
 */
export function useAccionesObjetivos(onCambio: () => Promise<void> | void) {
  const [moviendo, setMoviendo] = useState<string | null>(null)
  const [borrando, setBorrando] = useState(false)
  const confirmacion = useConfirmacion<Objetivo>()

  async function mover(id: string, estado: EstadoObjetivo) {
    setMoviendo(id)
    try {
      await cambiarEstadoObjetivo(id, { estado })
      await onCambio()
    } catch {
      toast.error("No se pudo mover el objetivo. Intentá de nuevo.")
    } finally {
      setMoviendo(null)
    }
  }

  async function confirmarBorrado() {
    const objetivo = confirmacion.pendiente
    if (!objetivo) return
    setBorrando(true)
    try {
      await deleteObjetivo(objetivo.id)
      confirmacion.cerrar()
      await onCambio()
    } catch {
      toast.error("No se pudo eliminar el objetivo. Intentá de nuevo.")
    } finally {
      setBorrando(false)
    }
  }

  return { moviendo, borrando, confirmacion, mover, confirmarBorrado }
}
