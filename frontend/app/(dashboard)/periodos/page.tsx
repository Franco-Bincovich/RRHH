"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
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
        /* ⚠️ NO HAY FILTROS NI PIE, y no faltan: `GET /api/periodos` no acepta un solo Query y
           devuelve la lista entera de la empresa activa. Sin filtros no hay chips que mostrar y
           sin `page` del backend no hay pie que armar. El recorte por empresa lo hace el header
           `X-Empresa-Id` del sidebar, como en el resto del sistema. */
        description="Cerrá un período para impedir cambios en registros con fecha dentro de ese rango."
        action={<ExportMenu onExport={exportarPeriodos} />}
      />
      <div className="space-y-4">
        {canWrite && <PeriodoForm onCreated={load} />}
        {/* 🔴 LOS TRES ESTADOS SON DE LA TABLA, no de la página: el vacío tiene que ser una fila
            con `colSpan` adentro de la `<Table>` para que el encabezado siga puesto (§3). Y ese
            vacío lleva COPY PROPIO —"mientras no haya ninguno, todo se puede editar"— porque el
            genérico del patrón le diría a `gerencia_lectura` que cargue el primero, cosa que no
            puede hacer. El porqué completo está en `PeriodoList`. */}
        <PeriodoList
          periodos={periodos}
          loading={loading}
          error={error}
          nombreUsuario={nombreUsuario}
          canWrite={canWrite}
          onRetry={load}
          onReabrir={handleReabrir}
        />
      </div>
    </div>
  )
}
