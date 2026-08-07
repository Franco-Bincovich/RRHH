"use client"

import { useAsignarEmpleados } from "@/components/features/proyectos/useAsignarEmpleados"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ErrorCarga } from "@/components/ui/ErrorCarga"

export const ERROR_CANDIDATOS = "No se pudieron cargar los empleados."

interface Props {
  open: boolean
  proyectoId: string
  /** Ids de los empleados YA asignados al proyecto. Llegan por prop desde EquipoTab, que los
   *  tiene para su propia lista: es lo que hace que el resumen del área no cueste un request. */
  yaAsignadosIds: string[]
  onClose: () => void
  onSuccess: () => void
}

const INPUT_CLS = "flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
const LABEL_CLS = "block text-xs font-medium text-foreground mb-1"

/**
 * Alta múltiple: por selección manual, o EL ÁREA ENTERA de una vez.
 *
 * El área hace las DOS cosas: filtra la lista de candidatos, y —desde el 2/8/2026— se puede
 * asignar completa con un botón. Antes solo filtraba; que no asignara no era una decisión de
 * diseño, era simplemente lo que estaba implementado.
 *
 * 🔴 EL RESUMEN DICE CUÁNTOS QUEDAN POR ASIGNAR, no cuántos tiene el área. Con la mitad del área
 * ya en el proyecto, "trae 9" engaña: se van a crear 4. Y el reparto real lo vuelve necesario —
 * 6 de las 9 áreas de producción tienen UNA sola persona, así que "asignar ANALISIS" y "asignar
 * SALUD" se ven idénticas antes de apretar y una asigna a 1 y la otra a 9.
 *
 * Sale de datos que ya están acá: los candidatos del área ya se piden server-side, y los ya
 * asignados llegan por prop desde EquipoTab, que los tiene para su propia lista. Cero requests.
 */
export function AsignarEmpleadosModal({ open, proyectoId, yaAsignadosIds, onClose, onSuccess }: Props) {
  const {
    empleados, areas, areaFiltro, setAreaFiltro, search, setSearch, sel, rol, setRol,
    valorHora, setValorHora, fechaDesde, setFechaDesde, fechaHasta, setFechaHasta,
    saving, asignandoArea, yaEnElProyecto, faltan, visibles, allSelected,
    toggle, toggleAll, handleSubmit, handleAsignarArea, errorCandidatos, recargarCandidatos,
  } = useAsignarEmpleados(open, proyectoId, yaAsignadosIds, onSuccess)

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle className="text-base">Asignar empleados</DialogTitle></DialogHeader>
        <div className="space-y-4 pt-2">
          <div className="grid grid-cols-2 gap-3">
            <select className={INPUT_CLS} value={areaFiltro} onChange={(e) => setAreaFiltro(e.target.value)} aria-label="Filtrar por área">
              <option value="">Todas las áreas</option>
              {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
            </select>
            <input className={INPUT_CLS} type="search" value={search} placeholder="Buscar por nombre…" onChange={(e) => setSearch(e.target.value)} />
          </div>

          {/* El resumen del área sale de `empleados`; con la carga fallida diría "no queda nadie
              por agregar" sobre una lista que nunca llegó. Se oculta junto con la lista. */}
          {areaFiltro && !errorCandidatos && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border bg-muted/30 px-3 py-2">
              <p className="text-xs text-muted-foreground">
                {empleados.length} en el área
                {yaEnElProyecto > 0 && <> · {yaEnElProyecto} ya asignado{yaEnElProyecto !== 1 ? "s" : ""}</>}
                {" · "}
                <strong className="text-foreground">
                  {faltan === 0 ? "no queda nadie por agregar" : `se van a agregar ${faltan}`}
                </strong>
              </p>
              <Button variant="outline" size="sm" onClick={handleAsignarArea}
                      disabled={asignandoArea || saving || faltan === 0 || !rol.trim()}>
                {asignandoArea ? "Asignando…" : "Asignar el área"}
              </Button>
            </div>
          )}

          {/* 🔴 "Sin candidatos." solo cuando la lista LLEGÓ y está vacía. Cuando la consulta
              falla, decir eso manda a RRHH a revisar las altas de empleados por un problema que
              está en la red o en el request — que es lo que pasó acá durante meses con el
              `page_size=200` que el backend rechazaba con 422. */}
          {errorCandidatos ? (
            <ErrorCarga mensaje={ERROR_CANDIDATOS} onReintentar={recargarCandidatos} />
          ) : (
          <div className="rounded-md border">
            <label className="flex items-center gap-2 border-b px-3 py-2 text-xs font-medium text-muted-foreground">
              <input type="checkbox" checked={allSelected} onChange={toggleAll} />
              Seleccionar todos ({sel.size} seleccionado{sel.size !== 1 ? "s" : ""})
            </label>
            <div className="max-h-52 divide-y overflow-y-auto">
              {visibles.length === 0 ? (
                <p className="px-3 py-6 text-center text-sm text-muted-foreground">Sin candidatos.</p>
              ) : visibles.map((e) => (
                <label key={e.id} className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm">
                  <input type="checkbox" checked={sel.has(e.id)} onChange={() => toggle(e.id)} />
                  <span className="flex-1 text-foreground">{e.nombre} {e.apellido}</span>
                  {e.empresa_nombre && <Badge variant="secondary" className="text-xs">{e.empresa_nombre}</Badge>}
                </label>
              ))}
            </div>
          </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 sm:col-span-1">
              <label className={LABEL_CLS}>Rol en el proyecto</label>
              <input className={INPUT_CLS} value={rol} onChange={(e) => setRol(e.target.value)} placeholder="Ej: Desarrollador" />
            </div>
            <div className="col-span-2 sm:col-span-1">
              <label className={LABEL_CLS}>Valor/hora (ARS)</label>
              <input type="number" min="0" step="100" className={INPUT_CLS} value={valorHora} onChange={(e) => setValorHora(e.target.value)} />
            </div>
            <div><label className={LABEL_CLS}>Desde</label><input type="date" className={INPUT_CLS} value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} /></div>
            <div><label className={LABEL_CLS}>Hasta</label><input type="date" className={INPUT_CLS} value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} /></div>
          </div>

          <p className="text-xs text-muted-foreground">Todos comparten rol, valor/hora y fechas. Editá cada uno después si difieren.</p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" className="min-h-[2.75rem]" onClick={onClose}>Cancelar</Button>
            <Button size="sm" className="min-h-[2.75rem]" onClick={handleSubmit} disabled={saving || sel.size === 0 || !rol.trim()}>
              {saving ? "Asignando…" : `Asignar (${sel.size})`}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
