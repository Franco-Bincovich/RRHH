"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { Pagination } from "@/components/ui/Pagination"
import { Skeleton } from "@/components/ui/skeleton"
import { ErrorState } from "@/components/ui/ErrorState"
import { useCanWrite } from "@/hooks/useCanWrite"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import {
  deleteVacacionPendiente, exportarVacacionesPendientes, fetchVacacionesPendientes,
  updateVacacionPendiente,
} from "@/services/vacacionesPendientes"
import type { VacacionPendiente } from "@/types/vacaciones"
import { PendientesTable } from "./PendientesTable"

const PAGE_SIZE = 20

interface PendientesSectionProps {
  showEmpresa: boolean
  /** Cambia cuando se crea un registro desde el modal, para refrescar esta sección. */
  refreshKey: number
}

/**
 * Sección de días NO tomados, debajo del listado de vacaciones tomadas.
 *
 * 🔴 Paginación PROPIA e independiente, y NO una tabla fusionada con la de arriba: son dos
 * fuentes distintas, y fusionarlas exigiría traer las dos enteras para poder ordenar y paginar
 * el resultado combinado. Con historia completa de 50-120 empleados por empresa eso es
 * exactamente el volumen que el límite de export existe para evitar.
 */
export function PendientesSection({ showEmpresa, refreshKey }: PendientesSectionProps) {
  const canWrite = useCanWrite()
  const [items, setItems] = useState<VacacionPendiente[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchVacacionesPendientes(page, PAGE_SIZE)
      setItems(data.items)
      setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [page, refreshKey])

  useEffect(() => { load() }, [load])

  async function conBusy(id: string, accion: () => Promise<unknown>, fallback: string) {
    setBusyId(id)
    try {
      await accion()
      await load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : fallback)
    } finally {
      setBusyId(null)
    }
  }

  // El tilde es binario, pero el dato de fondo es un entero: tildar liquida TODOS los días.
  const toggleLiquidada = (p: VacacionPendiente) => conBusy(
    p.id,
    () => updateVacacionPendiente(p.id, { dias_liquidados: p.dias_liquidados >= p.dias ? 0 : p.dias }),
    "No se pudo actualizar el registro. Intentá de nuevo.",
  )

  const eliminar = (id: string) => conBusy(
    id, () => deleteVacacionPendiente(id), "No se pudo eliminar el registro. Intentá de nuevo.",
  )

  return (
    <section className="mt-8" aria-label="Días de vacaciones pendientes">
      <div className="mb-1 flex items-start justify-between gap-2">
        <h2 className="text-base font-semibold text-foreground">Días pendientes</h2>
        {/* El archivo sale del MISMO listado que la tabla, con el mismo recorte por ownership
            que el backend resuelve con el token. Sin filas no se ofrece exportar. */}
        {!loading && !error && items.length > 0 && (
          <ExportMenu onExport={exportarVacacionesPendientes} />
        )}
      </div>
      <p className="mb-4 text-sm text-muted-foreground">
        Días de un período que no se tomaron. No tienen fechas porque nadie faltó ningún día.
        {!loading && !error && ` · ${total} registro${total !== 1 ? "s" : ""}`}
      </p>

      {loading && <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}</div>}
      {!loading && error && <ErrorState action={load} />}
      {!loading && !error && items.length === 0 && (
        <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          Sin días pendientes registrados.
        </p>
      )}

      {!loading && !error && items.length > 0 && (
        <PendientesTable
          items={items}
          canWrite={canWrite}
          showEmpresa={showEmpresa}
          busyId={busyId}
          onToggleLiquidada={toggleLiquidada}
          onDelete={eliminar}
        />
      )}

      {!loading && !error && total > PAGE_SIZE && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}
    </section>
  )
}
