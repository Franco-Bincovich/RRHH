"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { PeriodoForm } from "@/components/features/periodos/PeriodoForm"
import { PeriodoList } from "@/components/features/periodos/PeriodoList"
import { useCanWrite } from "@/hooks/useCanWrite"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarPeriodos, fetchPeriodos, reabrirPeriodo } from "@/services/periodos"
import { fetchUsuariosActivos } from "@/services/objetivos"
import type { Periodo } from "@/types/periodo"

export default function PeriodosPage() {
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [usuarios, setUsuarios] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const canWrite = useCanWrite("periodos")

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const [per, us] = await Promise.all([fetchPeriodos(), fetchUsuariosActivos()])
      setPeriodos(per.items)
      setUsuarios(Object.fromEntries(us.items.map((u) => [u.id, `${u.nombre} ${u.apellido}`])))
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  function nombreUsuario(id: string | null): string {
    return (id && usuarios[id]) || "—"
  }

  async function handleReabrir(p: Periodo) {
    if (!confirm(`¿Reabrir el período de ${p.desde} a ${p.hasta}? Se podrán volver a cargar y editar registros en ese rango.`)) return
    try {
      await reabrirPeriodo(p.id)
      toast.success("Período reabierto")
      await load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "No se pudo reabrir el período")
    }
  }

  return (
    <div>
      <PageHeader
        title="Períodos"
        description="Cerrá un período para impedir cambios en registros con fecha dentro de ese rango."
        action={<ExportMenu onExport={exportarPeriodos} />}
      />
      <div className="space-y-4">
        {canWrite && <PeriodoForm onCreated={load} />}
        {loading ? (
          <Skeleton className="h-40 w-full rounded-xl" />
        ) : error ? (
          <ErrorState action={load} />
        ) : periodos.length === 0 ? (
          <p className="rounded-xl border bg-card p-6 text-sm text-muted-foreground">
            Todavía no hay períodos cerrados.
          </p>
        ) : (
          <PeriodoList periodos={periodos} nombreUsuario={nombreUsuario} canWrite={canWrite} onReabrir={handleReabrir} />
        )}
      </div>
    </div>
  )
}
