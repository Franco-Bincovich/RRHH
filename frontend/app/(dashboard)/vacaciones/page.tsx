"use client"

import { useState } from "react"
import { Plus } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { VacacionesModal } from "@/components/features/vacaciones/VacacionesModal"
import { VacacionesTable } from "@/components/features/vacaciones/VacacionesTable"
import { VacacionesVistaMapa } from "@/components/features/vacaciones/VacacionesVistaMapa"
import { useFiltrosVacaciones } from "@/components/features/vacaciones/useFiltrosVacaciones"
import { useVacacionesLista, PAGE_SIZE } from "@/components/features/vacaciones/useVacacionesLista"
import { AdjuntosDialog } from "@/components/features/adjuntos/AdjuntosDialog"
import { PendientesSection } from "@/components/features/vacaciones/PendientesSection"
import { exportarVacaciones } from "@/services/vacaciones"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { useConfirmacion } from "@/components/features/shared/useConfirmacion"
import { confirmarCancelarVacaciones } from "@/components/features/shared/confirmaciones"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { SolicitudVacaciones } from "@/types/vacaciones"

type Vista = "lista" | "mapa"

export default function VacacionesPage() {
  const canWrite = useCanWrite()
  const [page, setPage] = useState(1)
  const [vista, setVista] = useState<Vista>("lista")
  const [modalOpen, setModalOpen] = useState(false)
  const [docsFor, setDocsFor] = useState<SolicitudVacaciones | null>(null)
  // El modal puede crear en cualquiera de las dos tablas, así que al guardar se refrescan las dos.
  const [pendientesKey, setPendientesKey] = useState(0)

  const { empresaActivaId, filtros, campos } = useFiltrosVacaciones(() => setPage(1))
  const { solicitudes, loading, error, total, cancelingId, load, handleCancel } =
    useVacacionesLista(filtros, page)

  const chips = chipsDeCampos(campos)

  /* 🔴 PIDE CONFIRMACIÓN, PERO NO ES UN BORRADO — y el texto lo dice. `cancel` setea
     `cancelada=true`: la fila sigue en el listado y los días vuelven al saldo (el cálculo filtra
     por `cancelada=false`). Escribirle el copy de un borrado frenaría al usuario de hacer algo
     reversible, y de paso devaluaría el diálogo de los que sí destruyen. Ver `confirmaciones.ts`. */
  const aCancelar = useConfirmacion<SolicitudVacaciones>()

  return (
    <div>
      <PageHeader
        title="Vacaciones"
        /* El conteo sale de `total` (el del filtro entero, del backend) y no del largo de la
           página: con paginación `solicitudes.length` es 20 en cualquier padrón. */
        description={loading ? "Cargando..." : `${total} registro${total !== 1 ? "s" : ""}`}
        action={
          <div className="flex gap-2">
            {!loading && !error && solicitudes.length > 0 && (
              <ExportMenu onExport={(f) => exportarVacaciones(f, filtros)} />
            )}
            {canWrite && (
              <Button className="min-h-11" onClick={() => setModalOpen(true)}>
                <Plus className="size-4" />
                Registrar vacaciones
              </Button>
            )}
          </div>
        }
      />

      <div className="mb-4 flex gap-1 rounded-lg bg-muted p-1 w-fit">
        <Button size="sm" variant={vista === "lista" ? "secondary" : "ghost"} onClick={() => setVista("lista")}>Lista</Button>
        <Button size="sm" variant={vista === "mapa" ? "secondary" : "ghost"} onClick={() => setVista("mapa")}>Mapa</Button>
      </div>

      {/* `panel`: la forma completa del patrón de filtros (caja propia, "Más filtros" y los chips
          de la fila inferior). `disabled` durante la carga: los controles quedan A LA VISTA con
          sus chips pero no se pueden tocar (§3). Los MISMOS filtros gobiernan las dos vistas. */}
      <FiltersBar campos={campos} panel disabled={loading} />

      {vista === "lista" ? (
        <VacacionesTable
          items={solicitudes}
          loading={loading}
          error={error}
          canWrite={canWrite}
          showEmpresa={!empresaActivaId}
          cancelingId={cancelingId}
          onRetry={load}
          onCancel={aCancelar.pedir}
          onDocs={setDocsFor}
          chips={chips}
          onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
          accionVacio={canWrite ? (
            <Button className="min-h-11" onClick={() => setModalOpen(true)}>Registrar las primeras</Button>
          ) : undefined}
        />
      ) : (
        <VacacionesVistaMapa
          items={solicitudes} loading={loading} error={error} onRetry={load} chips={chips}
        />
      )}

      {/*
       * 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS, no sólo cuando hay más de una página. Antes aparecía
       * con `total > PAGE_SIZE`: con pocos registros y un filtro puesto, la pantalla dejaba de
       * decir cuántos resultados había justo cuando el filtro es lo que hay que entender. El
       * total que muestra es el TOTAL FILTRADO del backend, no `solicitudes.length`.
       *
       * ⚠️ Sigue siendo SÓLO de la vista lista: el mapa muestra el mes entero y su unidad no es
       * la fila. Paginar un calendario no significa nada.
       */}
      {!loading && !error && vista === "lista" && solicitudes.length > 0 && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}

      {vista === "lista" && <PendientesSection showEmpresa={!empresaActivaId} refreshKey={pendientesKey} />}

      <VacacionesModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={() => { setModalOpen(false); load(); setPendientesKey((k) => k + 1) }}
      />

      <ConfirmDialog
        open={aCancelar.abierto}
        onClose={aCancelar.cerrar}
        onConfirm={() => {
          const s = aCancelar.pendiente
          aCancelar.cerrar()
          if (s) handleCancel(s.id)
        }}
        loading={cancelingId !== null}
        {...confirmarCancelarVacaciones(aCancelar.pendiente ?? {})}
      />

      <AdjuntosDialog
        open={!!docsFor}
        onClose={() => setDocsFor(null)}
        entidad="vacacion"
        entidadId={docsFor?.id ?? ""}
        titulo={`Vacación · ${docsFor?.empleado_nombre ?? ""}`}
      />
    </div>
  )
}
