"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { AsignacionesInvTable } from "@/components/features/inventario/AsignacionesInvTable"
import { AsignarModal } from "@/components/features/inventario/AsignarModal"
import { DevolverModal } from "@/components/features/inventario/DevolverModal"
import { useFiltrosAsignacionesInv } from "@/components/features/inventario/useFiltrosAsignacionesInv"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarInventarioAsignaciones, fetchAsignaciones } from "@/services/inventario"
import type { Asignacion } from "@/types/inventario"

export function AsignacionesTab({ canWrite }: { canWrite: boolean }) {
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [asignarModal, setAsignarModal] = useState(false)
  const [devolviendo, setDevolviendo] = useState<Asignacion | null>(null)
  // Este listado no pagina, así que no hay page que resetear.
  const { empresaActivaId, filtros, campos } = useFiltrosAsignacionesInv(() => {})

  const load = useCallback(async () => {
    setLoading(true); setError(false)
    try {
      const data = await fetchAsignaciones(filtros)
      setAsignaciones(data.items)
    } catch { setError(true) }
    finally { setLoading(false) }
    // filtros es un objeto nuevo por render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros)])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <FiltersBar campos={campos} />
        <div className="mb-4 flex gap-2">
          <ExportMenu onExport={(f) => exportarInventarioAsignaciones(f, filtros)} />
          {canWrite && (
            <Button className="min-h-11" onClick={() => setAsignarModal(true)}>
              <Plus className="size-4" /> Asignar ítem
            </Button>
          )}
        </div>
      </div>

      <AsignacionesInvTable
        asignaciones={asignaciones} loading={loading} error={error} canWrite={canWrite}
        mostrarEmpresa={!empresaActivaId} onReload={load} onDevolver={setDevolviendo}
      />

      <AsignarModal open={asignarModal} onClose={() => setAsignarModal(false)} onSuccess={() => { setAsignarModal(false); load() }} />
      {devolviendo && (
        <DevolverModal asignacion={devolviendo} onClose={() => setDevolviendo(null)} onSuccess={() => { setDevolviendo(null); load() }} />
      )}
    </div>
  )
}
