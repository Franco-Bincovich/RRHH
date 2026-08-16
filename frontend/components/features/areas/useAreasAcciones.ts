"use client"

import { useState } from "react"
import { toast } from "sonner"

import { deleteArea } from "@/services/areas"
import type { Area } from "@/types/area"

/**
 * El ABM de la pantalla de áreas: el modal de alta/edición y el borrado con confirmación.
 *
 * Hook aparte de `useAreas` porque son dos responsabilidades con ciclos de vida distintos —la
 * lista se recarga al buscar o cambiar de página, el modal no— y juntas pasaban el límite de 80
 * al sumarle la paginación. Mismo criterio que `useEdicionNomina`, que salió de `useNominaLista`.
 *
 * ⚠️ `onCambio` lo dispara el borrado Y el alta/edición: las dos cosas cambian el TOTAL, no sólo
 * las filas. Recargar la lista es lo que mantiene el contador del encabezado sincronizado — con
 * paginación, borrar la última fila de la página 3 además puede dejarte en una página que ya no
 * existe, y quien recarga es el caller.
 */
export function useAreasAcciones(onCambio: () => void) {
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Area | undefined>(undefined)
  const [confirmDelete, setConfirmDelete] = useState<Area | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function handleDelete() {
    if (!confirmDelete) return
    setDeleting(true)
    try {
      await deleteArea(confirmDelete.id)
      setConfirmDelete(null)
      onCambio()
    } catch {
      toast.error("No se pudo eliminar el área. Intentá de nuevo.")
    } finally {
      setDeleting(false)
    }
  }

  return {
    modalOpen, setModalOpen, editing, confirmDelete, setConfirmDelete, deleting, handleDelete,
    openCreate: () => { setEditing(undefined); setModalOpen(true) },
    openEdit: (a: Area) => { setEditing(a); setModalOpen(true) },
    onModalSuccess: () => { setModalOpen(false); onCambio() },
  }
}
