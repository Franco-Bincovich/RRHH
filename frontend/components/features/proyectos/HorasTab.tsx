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
  // 🔴 Los totales son ESTADO propio traído del backend, no un derivado de `horas`. Ver abajo.
  const [totalHoras, setTotalHoras]     = useState(0)
  const [totalCosto, setTotalCosto]     = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [h, a] = await Promise.all([fetchHoras(proyectoId, page, PAGE_SIZE), fetchAsignaciones(proyectoId)])
      setHoras(h.items); setTotal(h.total); setAsignaciones(a.items)
      setTotalHoras(h.total_horas); setTotalCosto(h.total_costo)
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

  // 🔴 ACA HABIA DOS `.reduce()` SOBRE `horas`, Y `horas` ES UNA PAGINA. El pie decía "9 h"
  // sobre un proyecto de 400 y el número cambiaba al pasar de página — un total que se mueve al
  // navegar no es un total, y nada en la pantalla delataba que estaba mal.
  // Ahora los dos vienen del backend (`total_horas` / `total_costo`), calculados sobre TODAS las
  // cargas del proyecto en `_proyectos_enrich.totales_de_proyecto`.
  //
  // ⚠️ NO los vuelvas a derivar de `horas` "para no pedir un campo más": el bug es invisible
  // mientras el proyecto entre en una página, que es exactamente el caso en el que se prueba.
  //
  // Las cargas del link público no tienen `valor_hora_snapshot` con qué costear y suman 0 al
  // total —para un TOTAL, "no costeable" aporta cero— pero abajo NO se imprimen como "$ 0": eso
  // diría que costaron nada. Ver types/proyecto.ts::Hora.

  if (loading) return (
    <div className="space-y-2 animate-pulse">
      {[1, 2, 3].map((i) => <div key={i} className="h-12 rounded-lg bg-muted" />)}
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {/* 🔴 DECÍA "esta página:", y era CIERTO mientras los números salían de un `.reduce()`
              sobre `horas`. Ahora son del proyecto entero, así que el texto tenía que cambiar
              con ellos: dejarlo habría convertido un subtotal honesto en un total mal rotulado,
              que es peor que el punto de partida. Si un número cambia de alcance, su etiqueta
              es parte del cambio. */}
          {total} registro{total !== 1 ? "s" : ""} · {totalHoras.toFixed(1)} h · {ARS.format(totalCosto)} en todo el proyecto
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
