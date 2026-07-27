"use client"

import { useCallback, useEffect, useState } from "react"
import { AlertCircle, Pencil, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { AsignacionModal } from "@/components/features/capacitaciones/AsignacionModal"
import { CertificadoCell } from "@/components/features/capacitaciones/CertificadoCell"
import { EstadoModal } from "@/components/features/capacitaciones/EstadoModal"
import { fetchAsignaciones, deleteAsignacion, exportarCapacitaciones } from "@/services/capacitaciones"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { fetchEmpresas } from "@/services/empresas"
import { fetchAreas } from "@/services/areas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Asignacion } from "@/types/capacitacion"
import type { Empresa } from "@/types/empresa"
import type { Area } from "@/types/area"

const SELECT_CLASS =
  "min-h-[2rem] rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

const ESTADO_BADGE: Record<string, "default" | "secondary" | "outline"> = {
  pendiente: "outline", en_curso: "secondary", completado: "default",
}
const ESTADO_LABEL: Record<string, string> = {
  pendiente: "Pendiente", en_curso: "En curso", completado: "Completado",
}

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
    </div>
  )
}

function formatFecha(s: string | null): string {
  if (!s) return "—"
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y}`
}

export function AsignacionesTab({ canWrite }: { canWrite: boolean }) {
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [areas, setAreas] = useState<Area[]>([])
  const [areaFiltro, setAreaFiltro] = useState("")
  const [estadoFiltro, setEstadoFiltro] = useState("")
  const [asignacionModal, setAsignacionModal] = useState(false)
  const [estadoModal, setEstadoModal] = useState<Asignacion | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (!empresaActivaId) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [empresaActivaId])

  useEffect(() => {
    const empId = empresaActivaId || empresaFiltro || undefined
    fetchAreas(empId).then(setAreas).catch(() => setAreas([]))
  }, [empresaActivaId, empresaFiltro])

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const override = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined
      const data = await fetchAsignaciones({
        empresaIdOverride: override,
        estado: estadoFiltro || undefined,
        areaId: areaFiltro || undefined,
      })
      setAsignaciones(data.items)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [empresaActivaId, empresaFiltro, estadoFiltro, areaFiltro])

  useEffect(() => { load() }, [load])

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await deleteAsignacion(id); await load() }
    catch { toast.error("No se pudo eliminar la asignación. Intentá de nuevo.") }
    finally { setDeletingId(null) }
  }

  const mostrarFiltroEmpresa = !empresaActivaId && empresas.length > 0

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {mostrarFiltroEmpresa && (
            <select aria-label="Filtrar por empresa" className={SELECT_CLASS} value={empresaFiltro} onChange={(e) => { setEmpresaFiltro(e.target.value); setAreaFiltro("") }}>
              <option value="">Todas las empresas</option>
              {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
            </select>
          )}
          {areas.length > 0 && (
            <select aria-label="Filtrar por área" className={SELECT_CLASS} value={areaFiltro} onChange={(e) => setAreaFiltro(e.target.value)}>
              <option value="">Todas las áreas</option>
              {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
            </select>
          )}
          <select aria-label="Filtrar por estado" className={SELECT_CLASS} value={estadoFiltro} onChange={(e) => setEstadoFiltro(e.target.value)}>
            <option value="">Todos los estados</option>
            <option value="pendiente">Pendiente</option>
            <option value="en_curso">En curso</option>
            <option value="completado">Completado</option>
          </select>
        </div>
        <div className="flex gap-2">
          {!loading && !error && asignaciones.length > 0 && (
            <ExportMenu onExport={(f) => exportarCapacitaciones(f, { empresaIdOverride: !empresaActivaId && empresaFiltro ? empresaFiltro : undefined, estado: estadoFiltro || undefined, areaId: areaFiltro || undefined })} />
          )}
          {canWrite && (
            <Button className="min-h-11" onClick={() => setAsignacionModal(true)}>
              <Plus className="size-4" /> Asignar
            </Button>
          )}
        </div>
      </div>

      {loading && <TableSkeleton />}
      {!loading && error && <ErrorState action={load} />}
      {!loading && !error && asignaciones.length === 0 && (
        <EmptyState icon={<AlertCircle />} title="Sin asignaciones" description="No hay asignaciones que coincidan con los filtros." />
      )}

      {!loading && !error && asignaciones.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Empleado</TableHead>
              <TableHead>Capacitación</TableHead>
              <TableHead>Estado</TableHead>
              {!empresaActivaId && <TableHead>Empresa</TableHead>}
              <TableHead>Fecha límite</TableHead>
              <TableHead>Completado</TableHead>
              <TableHead>Certificado</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {asignaciones.map((a) => (
              <TableRow key={a.id}>
                <TableCell className="font-medium">{a.empleado_nombre ?? "—"}</TableCell>
                <TableCell>{a.capacitacion_nombre ?? "—"}</TableCell>
                <TableCell>
                  <Badge variant={ESTADO_BADGE[a.estado] ?? "outline"}>{ESTADO_LABEL[a.estado] ?? a.estado}</Badge>
                </TableCell>
                {!empresaActivaId && <TableCell className="text-muted-foreground">{a.empresa_nombre ?? "—"}</TableCell>}
                <TableCell className="text-muted-foreground">{formatFecha(a.fecha_limite)}</TableCell>
                <TableCell className="text-muted-foreground">{formatFecha(a.fecha_completado)}</TableCell>
                <TableCell>
                  <CertificadoCell
                    asignacionId={a.id}
                    hasCertificado={Boolean(a.certificado_url)}
                    canWrite={canWrite}
                    onUploaded={load}
                  />
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    {canWrite && (
                      <>
                        <Button variant="ghost" size="sm" onClick={() => setEstadoModal(a)} aria-label="Cambiar estado">
                          <Pencil className="size-3.5" />
                        </Button>
                        <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" disabled={deletingId === a.id} onClick={() => handleDelete(a.id)} aria-label="Eliminar">
                          {deletingId === a.id ? "..." : <Trash2 className="size-3.5" />}
                        </Button>
                      </>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <AsignacionModal
        open={asignacionModal}
        onClose={() => setAsignacionModal(false)}
        onSuccess={() => { setAsignacionModal(false); load() }}
      />

      {estadoModal && (
        <EstadoModal
          open={Boolean(estadoModal)}
          asignacion={estadoModal}
          onClose={() => setEstadoModal(null)}
          onSuccess={() => { setEstadoModal(null); load() }}
        />
      )}
    </div>
  )
}
