"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Pagination } from "@/components/ui/Pagination"
import { HoraModal } from "./HoraModal"
import { fetchHoras, fetchAsignaciones, createHora, deleteHora } from "@/services/proyectos"
import type { Asignacion, Hora, HoraCreate } from "@/types/proyecto"

const ARS = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 })
const PAGE_SIZE = 20

function formatFecha(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

interface Props {
  proyectoId: string
  onRefresh: () => Promise<void>   // notifica al padre para refrescar el costeo
  canWrite: boolean
}

export function HorasTab({ proyectoId, onRefresh, canWrite }: Props) {
  const [horas, setHoras]               = useState<Hora[]>([])
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading]           = useState(true)
  const [modalOpen, setModalOpen]       = useState(false)
  const [page, setPage]                 = useState(1)
  const [total, setTotal]               = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [h, a] = await Promise.all([fetchHoras(proyectoId, page, PAGE_SIZE), fetchAsignaciones(proyectoId)])
      setHoras(h.items); setTotal(h.total); setAsignaciones(a.items)
    } catch { toast.error("No se pudieron cargar las horas.") }
    finally { setLoading(false) }
  }, [proyectoId, page])

  useEffect(() => { load() }, [load])

  async function handleSave(body: HoraCreate) {
    try {
      await createHora(proyectoId, body)
      toast.success("Horas registradas")
      setModalOpen(false)
      await load()
      await onRefresh()
    } catch { toast.error("No se pudieron registrar las horas.") }
  }

  async function handleDelete(hora: Hora) {
    if (!confirm(`¿Eliminar ${hora.horas}h del ${formatFecha(hora.fecha)}?`)) return
    try {
      await deleteHora(proyectoId, hora.id)
      toast.success("Registro eliminado")
      await load()
      await onRefresh()
    } catch { toast.error("No se pudo eliminar el registro.") }
  }

  const totalHoras = horas.reduce((s, h) => s + h.horas, 0)
  // `costo` y `valor_hora_snapshot` son null en las cargas del link público (no tienen
  // `valor_hora_snapshot` con qué costear). Se suman como 0 —para un TOTAL, "no costeable"
  // aporta cero— pero abajo NO se imprimen como "$ 0": eso diría que costaron nada, cuando lo
  // cierto es que no se pueden costear. Ver types/proyecto.ts::Hora.
  const totalCosto = horas.reduce((s, h) => s + (h.costo ?? 0), 0)

  if (loading) return (
    <div className="space-y-2 animate-pulse">
      {[1, 2, 3].map((i) => <div key={i} className="h-12 rounded-lg bg-muted" />)}
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {total} registro{total !== 1 ? "s" : ""} en total · esta página: {totalHoras.toFixed(1)} h · {ARS.format(totalCosto)}
        </p>
        {canWrite && (
          <Button size="sm" className="min-h-[2.75rem] gap-1.5" onClick={() => setModalOpen(true)}>
            <Plus className="size-4" /> Cargar horas
          </Button>
        )}
      </div>

      {horas.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">Sin horas registradas.</p>
      ) : (
        <div className="divide-y divide-border rounded-xl border bg-card">
          {horas.map((h) => (
            <div key={h.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-medium text-foreground">{h.empleado_nombre}</span>
                  {h.empleado_empresa_nombre && (
                    <span className="text-xs text-muted-foreground">· {h.empleado_empresa_nombre}</span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {formatFecha(h.fecha)} · {h.horas}h{h.valor_hora_snapshot !== null ? ` · ${ARS.format(h.valor_hora_snapshot)}/h` : ""}
                  {h.descripcion ? ` · ${h.descripcion}` : ""}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <span className="text-sm font-semibold tabular-nums text-foreground">
                  {/* "—" y no "$ 0": una carga sin `valor_hora_snapshot` no se puede costear,
                      que no es lo mismo que haber costado cero. */}
                  {h.costo !== null ? ARS.format(h.costo) : "—"}
                </span>
                {canWrite && (
                  <Button variant="ghost" size="icon" className="size-8 text-destructive hover:text-destructive"
                    onClick={() => handleDelete(h)}>
                    <Trash2 className="size-3.5" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {total > PAGE_SIZE && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}

      <HoraModal open={modalOpen} proyectoId={proyectoId} asignaciones={asignaciones}
        onClose={() => setModalOpen(false)} onSave={handleSave} />
    </div>
  )
}
