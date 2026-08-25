"use client"

import { useCallback, useEffect, useState } from "react"
import { ApiError } from "@/services/api"
import { avisarHecho } from "@/components/features/shared/avisoGuardado"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { confirmarEliminarHoras } from "@/components/features/shared/confirmaciones"
import { useConfirmacion } from "@/components/features/shared/useConfirmacion"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Pagination } from "@/components/ui/Pagination"
import { HoraFila } from "./HoraFila"
import { HoraModal } from "./HoraModal"
import { fetchHoras, fetchAsignaciones, createHora, deleteHora } from "@/services/proyectos"
import type { Asignacion, Hora, HoraCreate } from "@/types/proyecto"

const ARS = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 })
const PAGE_SIZE_INICIAL = 20

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
  const aBorrar = useConfirmacion<Hora>()
  const [borrando, setBorrando] = useState<string | null>(null)
  const [loading, setLoading]           = useState(true)
  const [modalOpen, setModalOpen]       = useState(false)
  const [page, setPage]                 = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)
  const [total, setTotal]               = useState(0)
  // 🔴 Los totales son ESTADO propio traído del backend, no un derivado de `horas`. Ver abajo.
  const [totalHoras, setTotalHoras]     = useState(0)
  const [totalCosto, setTotalCosto]     = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [h, a] = await Promise.all([fetchHoras(proyectoId, page, pageSize), fetchAsignaciones(proyectoId)])
      setHoras(h.items); setTotal(h.total); setAsignaciones(a.items)
      setTotalHoras(h.total_horas); setTotalCosto(h.total_costo)
    } catch { toast.error("No se pudieron cargar las horas.") }
    finally { setLoading(false) }
  }, [proyectoId, page, pageSize])

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
    setBorrando(hora.id)
    try {
      await deleteHora(proyectoId, hora.id)
      avisarHecho("Carga de horas eliminada")
      await load()
      await onRefresh()
    } catch (e) { toast.error(e instanceof ApiError ? e.message : "No se pudo eliminar la carga.") }
    finally { setBorrando(null) }
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
            <HoraFila key={h.id} hora={h} canWrite={canWrite} onPedirBaja={aBorrar.pedir} />
          ))}
        </div>
      )}

      {total > pageSize && (
        <Pagination page={page} total={total} pageSize={pageSize} onPageSizeChange={setPageSize} onPageChange={setPage} />
      )}

      <HoraModal open={modalOpen} proyectoId={proyectoId} asignaciones={asignaciones}
        onClose={() => setModalOpen(false)} onSave={handleSave} />

      <ConfirmDialog
        open={aBorrar.abierto}
        onClose={aBorrar.cerrar}
        onConfirm={() => {
          const x = aBorrar.pendiente
          aBorrar.cerrar()
          if (x) void handleDelete(x)
        }}
        loading={borrando !== null}
        {...confirmarEliminarHoras(aBorrar.pendiente ?? {})}
      />
    </div>
  )
}
