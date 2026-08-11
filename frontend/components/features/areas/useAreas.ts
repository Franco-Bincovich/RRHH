"use client"

import { useState, useEffect, useMemo } from "react"
import { toast } from "sonner"

import { fetchAreas, deleteArea } from "@/services/areas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Area } from "@/types/area"

/**
 * Estado y acciones de la pantalla de áreas. Extraído de `areas/page.tsx` (271/150), que quedó
 * como orquestador de layout. Molde: `components/features/sucesion/`, donde el mismo corte bajó
 * una pantalla de 855 a 85.
 *
 * ⚠️ El buscador es CLIENT-SIDE (`filtradas`): con 12 áreas es tolerable, pero el export trae
 * TODAS las de la empresa, no las que el buscador deja a la vista. El día que crezca, ese
 * `search` tiene que pasar al backend (invariante 1 del bloque B).
 */
export function useAreas() {
  const [areas, setAreas] = useState<Area[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [search, setSearch] = useState("")
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Area | undefined>(undefined)
  const [confirmDelete, setConfirmDelete] = useState<Area | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function load() {
    setLoading(true)
    setError(false)
    try {
      setAreas(await fetchAreas(getEmpresaActivaId() ?? undefined))
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const filtradas = useMemo(() => {
    if (!search.trim()) return areas
    const q = search.trim().toLowerCase()
    return areas.filter((a) => a.nombre.toLowerCase().includes(q))
  }, [areas, search])

  async function handleDelete() {
    if (!confirmDelete) return
    setDeleting(true)
    try {
      await deleteArea(confirmDelete.id)
      setConfirmDelete(null)
      void load()
    } catch {
      toast.error("No se pudo eliminar el área. Intentá de nuevo.")
    } finally {
      setDeleting(false)
    }
  }

  return {
    areas, filtradas, loading, error, search, setSearch,
    modalOpen, setModalOpen, editing, confirmDelete, setConfirmDelete, deleting,
    load, handleDelete,
    openCreate: () => { setEditing(undefined); setModalOpen(true) },
    openEdit: (a: Area) => { setEditing(a); setModalOpen(true) },
    onModalSuccess: () => { setModalOpen(false); void load() },
  }
}
