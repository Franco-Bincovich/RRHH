"use client"

import { useCallback, useEffect, useState } from "react"
import { AlertCircle, Plus } from "lucide-react"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { AsignarModal } from "@/components/features/inventario/AsignarModal"
import { DevolverModal } from "@/components/features/inventario/DevolverModal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarInventarioAsignaciones, fetchAsignaciones } from "@/services/inventario"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Asignacion } from "@/types/inventario"
import type { Empresa } from "@/types/empresa"

const SEL = "min-h-[2rem] rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

function Skeleton5() {
  return <div className="space-y-2">{Array.from({length:5}).map((_,i)=><Skeleton key={i} className="h-12 w-full rounded-lg"/>)}</div>
}

function formatDate(s: string | null) {
  if (!s) return "—"
  const [y,m,d] = s.split("-"); return `${d}/${m}/${y}`
}

export function AsignacionesTab({ canWrite }: { canWrite: boolean }) {
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [asignarModal, setAsignarModal] = useState(false)
  const [devolviendo, setDevolviendo] = useState<Asignacion | null>(null)

  useEffect(() => {
    if (!empresaActivaId)
      fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [empresaActivaId])

  const load = useCallback(async () => {
    setLoading(true); setError(false)
    try {
      const override = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined
      const data = await fetchAsignaciones({ empresaIdOverride: override })
      setAsignaciones(data.items)
    } catch { setError(true) }
    finally { setLoading(false) }
  }, [empresaActivaId, empresaFiltro])

  useEffect(() => { load() }, [load])

  const mostrarEmpresa = !empresaActivaId

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {mostrarEmpresa && empresas.length > 0 && (
            <select className={SEL} value={empresaFiltro} onChange={(e) => setEmpresaFiltro(e.target.value)} aria-label="Filtrar por empresa">
              <option value="">Todas las empresas</option>
              {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
            </select>
          )}
        </div>
        <div className="flex gap-2">
          <ExportMenu onExport={(f) => exportarInventarioAsignaciones(f, { empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined })} />
          {canWrite && (
            <Button className="min-h-11" onClick={() => setAsignarModal(true)}>
              <Plus className="size-4" /> Asignar ítem
            </Button>
          )}
        </div>
      </div>

      {loading && <Skeleton5 />}
      {!loading && error && <ErrorState action={load} />}
      {!loading && !error && asignaciones.length === 0 && (
        <EmptyState icon={<AlertCircle />} title="Sin asignaciones activas" description="No hay ítems asignados actualmente." />
      )}
      {!loading && !error && asignaciones.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Empleado</TableHead>
              <TableHead>Ítem</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>N° Serie</TableHead>
              {mostrarEmpresa && <TableHead>Empresa</TableHead>}
              <TableHead>Desde</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {asignaciones.map((a) => (
              <TableRow key={a.id}>
                <TableCell className="font-medium">{a.empleado_nombre ?? "—"}</TableCell>
                <TableCell>{a.item_nombre ?? "—"}</TableCell>
                <TableCell className="text-muted-foreground">{a.item_tipo ?? "—"}</TableCell>
                <TableCell className="text-muted-foreground">{a.item_numero_serie ?? "—"}</TableCell>
                {mostrarEmpresa && <TableCell className="text-muted-foreground">{a.empresa_nombre ?? "—"}</TableCell>}
                <TableCell className="text-muted-foreground">{formatDate(a.fecha_asignacion)}</TableCell>
                <TableCell>
                  {canWrite && (
                    <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setDevolviendo(a)}>
                      Devolver
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      <AsignarModal open={asignarModal} onClose={() => setAsignarModal(false)} onSuccess={() => { setAsignarModal(false); load() }} />
      {devolviendo && (
        <DevolverModal asignacion={devolviendo} onClose={() => setDevolviendo(null)} onSuccess={() => { setDevolviendo(null); load() }} />
      )}
    </div>
  )
}
