"use client"

import { useState } from "react"
import { CalendarHeart, Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Pagination } from "@/components/ui/Pagination"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { EventoModal } from "@/components/features/eventos/EventoModal"
import { EventosTabla } from "@/components/features/eventos/EventosTabla"
import { PAGE_SIZE, useEventos } from "@/components/features/eventos/useEventos"
import { deleteEvento } from "@/services/eventos"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Evento } from "@/types/evento"

/**
 * Agenda de eventos. ORQUESTADOR: abre y cierra diálogos; el estado de DATOS vive en
 * `useEventos`, la tabla y el formulario en `components/features/eventos/`, y la carga en
 * `cargarEventos.ts` (testeable sin jsdom).
 *
 * ⚠️ NO HAY EXPORT, por decisión de producto: una agenda de recordatorios no es un dato que se
 * lleve a Excel; lo que se hace con un evento es resolverlo. Por eso tampoco hay `ExportMenu`
 * acá, a diferencia del resto de los listados.
 */
export default function EventosPage() {
  const canWrite = useCanWrite()
  const agenda = useEventos()
  const [modalOpen, setModalOpen] = useState(false)
  const [editando, setEditando] = useState<Evento | undefined>(undefined)
  const [aBorrar, setABorrar] = useState<Evento | null>(null)
  const [borrando, setBorrando] = useState(false)

  function abrirAlta() { setEditando(undefined); setModalOpen(true) }
  function abrirEdicion(e: Evento) { setEditando(e); setModalOpen(true) }

  async function confirmarBaja() {
    if (!aBorrar) return
    setBorrando(true)
    try {
      await deleteEvento(aBorrar.id)
      setABorrar(null)
      void agenda.load()
    } catch {
      toast.error("No se pudo eliminar el evento. Intentá de nuevo.")
    } finally {
      setBorrando(false)
    }
  }

  if (agenda.loading) {
    return (
      <div>
        <PageHeader title="Eventos" description="Cargando..." />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (agenda.error) {
    return (
      <div>
        <PageHeader title="Eventos" />
        <ErrorState description={agenda.error} action={agenda.load} />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Eventos"
        description={`${agenda.total} evento${agenda.total !== 1 ? "s" : ""}`}
        action={
          <div className="flex items-center gap-2">
            <Button variant="outline" className="min-h-11" onClick={agenda.alternarResueltas}>
              {agenda.incluirResueltas ? "Ocultar resueltos" : "Ver resueltos"}
            </Button>
            {canWrite && (
              <Button className="min-h-11" onClick={abrirAlta}>
                <Plus />
                Nuevo evento
              </Button>
            )}
          </div>
        }
      />

      {agenda.eventos.length === 0 ? (
        <EmptyState
          icon={<CalendarHeart />}
          title="Sin eventos"
          description="Todavía no hay eventos cargados. Creá el primero y va a aparecer en el dashboard cuando se acerque."
          action={canWrite ? (
            <Button className="min-h-11" onClick={abrirAlta}><Plus />Nuevo evento</Button>
          ) : undefined}
        />
      ) : (
        <>
          <EventosTabla eventos={agenda.eventos} canWrite={canWrite}
                        onEdit={abrirEdicion} onDelete={setABorrar}
                        onResuelta={agenda.cambiarResuelta} />
          <Pagination page={agenda.page} total={agenda.total} pageSize={PAGE_SIZE}
                      onPageChange={agenda.setPage} />
        </>
      )}

      <EventoModal
        open={modalOpen}
        evento={editando}
        onClose={() => setModalOpen(false)}
        onSuccess={() => { setModalOpen(false); void agenda.load() }}
      />

      <ConfirmDialog
        open={Boolean(aBorrar)}
        onClose={() => setABorrar(null)}
        onConfirm={confirmarBaja}
        loading={borrando}
        title="Eliminar el evento"
        description={`"${aBorrar?.nombre}" se borra definitivamente y deja de aparecer en el dashboard. La baja queda registrada en la auditoría.`}
        confirmLabel="Eliminar"
      />
    </div>
  )
}
