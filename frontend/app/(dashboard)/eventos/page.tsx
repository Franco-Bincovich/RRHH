"use client"

import { useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { EventoModal } from "@/components/features/eventos/EventoModal"
import { EventosTabla } from "@/components/features/eventos/EventosTabla"
import { construirCampos } from "@/components/features/eventos/_camposEventos"
import { PAGE_SIZE, useEventos } from "@/components/features/eventos/useEventos"
import { deleteEvento } from "@/services/eventos"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Evento } from "@/types/evento"

/**
 * Agenda. ORQUESTADOR: abre y cierra diálogos; el estado de DATOS vive en
 * `useEventos`, la tabla y el formulario en `components/features/eventos/`, y la carga en
 * `cargarEventos.ts` (testeable sin jsdom).
 *
 * ⚠️ NO HAY EXPORT, por decisión de producto: una agenda de recordatorios no es un dato que se
 * lleve a Excel; lo que se hace con un recordatorio es resolverlo. Por eso tampoco hay
 * `ExportMenu` acá, a diferencia del resto de los listados — y es la única pantalla sin él.
 *
 * 🔴 "AGENDA" (la pantalla) y "RECORDATORIO" (cada fila) — renombrado el 23/8/2026, antes era
 * "Eventos". Dos razones, y la segunda es la que cierra la discusión:
 *   · "Evento" no decía nada: puede ser cualquier cosa. Esto son fechas con días de anticipación.
 *   · El sistema YA usaba "evento" para OTRA cosa —el `evento` de la AUDITORÍA, columna de
 *     /auditoria y del export—, o sea dos conceptos con el mismo nombre en el mismo menú. Y ya
 *     usaba "Agenda" para ÉSTA: es el badge que "Requiere tu atención" le pone a estas filas en
 *     el dashboard, así que el usuario veía un badge sin pantalla que le correspondiera. Se
 *     eligió el nombre que el producto ya estaba usando. ("Avisos" habría sido el TERCER
 *     sinónimo del dashboard, y nombra el efecto y no la cosa: el mismo error que "Eventos".)
 *
 * ⚠️ EL RENOMBRE ES SÓLO DE TEXTO VISIBLE. Siguen igual: la ruta `/eventos`, la tabla
 * `eventos_agenda`, los endpoints `/api/eventos`, `Seccion.EVENTOS`, los `code` de error
 * (`EVENTO_NOT_FOUND`) y el valor `entidad` de auditoría. Misma regla que el renombre a
 * "Colaboradores": cambiar un `entidad` reescribe el significado de las filas ya guardadas.
 */
export default function EventosPage() {
  const canWrite = useCanWrite()
  const agenda = useEventos()
  const [modalOpen, setModalOpen] = useState(false)
  const [editando, setEditando] = useState<Evento | undefined>(undefined)
  const [aBorrar, setABorrar] = useState<Evento | null>(null)
  const [borrando, setBorrando] = useState(false)

  const campos = construirCampos({
    resueltosFiltro: agenda.resueltosFiltro,
    // El reset a página 1 ya vive dentro de este setter, en `useEventos`.
    setResueltosFiltro: agenda.setResueltosFiltro,
    onFiltroChange: () => {},
  })
  const chips = chipsDeCampos(campos)

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
      toast.error("No se pudo eliminar el recordatorio. Intentá de nuevo.")
    } finally {
      setBorrando(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Agenda"
        /* El conteo sale de `total` (el del filtro entero, del backend). 🔴 EL SUBTÍTULO EXPLICA
           QUÉ SON, NO REPITE EL NOMBRE: quién los carga, que llevan fecha, y que el aviso sale
           los días previos que se le indiquen. "Agenda · tu agenda" no le enseña nada a nadie. */
        description={
          agenda.loading && agenda.total === 0
            ? "Fechas que Capital Humano anota a mano para que el dashboard las avise con anticipación"
            : `${agenda.total} recordatorio${agenda.total !== 1 ? "s" : ""} · cada uno avisa en el dashboard los días previos que le pongas`
        }
        action={
          canWrite ? (
            <Button className="min-h-11" onClick={abrirAlta}>
              <Plus />
              Nuevo recordatorio
            </Button>
          ) : undefined
        }
      />

      {/* `panel`: la forma completa del patrón de filtros (caja propia y los chips de la fila
          inferior). Un solo control, así que no hay "Más filtros" — ver `_camposEventos.ts`. */}
      <FiltersBar campos={campos} panel disabled={agenda.loading} />

      <EventosTabla
        eventos={agenda.eventos}
        loading={agenda.loading}
        error={agenda.error}
        canWrite={canWrite}
        onRetry={agenda.load}
        onEdit={abrirEdicion}
        onDelete={setABorrar}
        onResuelta={agenda.cambiarResuelta}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? (
          <Button className="min-h-11" onClick={abrirAlta}>Crear el primero</Button>
        ) : undefined}
      />

      {/*
       * 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS y sólo después de cargar. Antes la barra colgaba del
       * bloque `eventos.length > 0`, que a su vez estaba protegido por los `return` tempranos de
       * carga y error; al mover los estados adentro de la tabla esa protección desaparece, así
       * que la guarda pasa a ser explícita. Sin ella, la barra quedaría mostrando el total del
       * pedido ANTERIOR sobre el esqueleto. El total es el del backend, no `eventos.length`.
       */}
      {!agenda.loading && !agenda.error && agenda.eventos.length > 0 && (
        <Pagination page={agenda.page} total={agenda.total} pageSize={PAGE_SIZE}
                    onPageChange={agenda.setPage} />
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
        title="Eliminar el recordatorio"
        description={`"${aBorrar?.nombre}" se borra definitivamente y deja de aparecer en el dashboard. La baja queda registrada en la auditoría.`}
        confirmLabel="Eliminar"
      />
    </div>
  )
}
