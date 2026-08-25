"use client"

import { useCallback, useEffect, useMemo, useState } from "react"

import { PageHeader } from "@/components/layout/PageHeader"
import { AuditTable } from "@/components/features/auditoria/AuditTable"
import { AuditDetailModal } from "@/components/features/auditoria/AuditDetailModal"
import { construirCampos } from "@/components/features/auditoria/_camposAuditoria"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { FiltersBar, type RangoFechas } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { exportarAuditoria, fetchAuditoria, type AuditoriaFiltros } from "@/services/auditoria"
import { fetchUsuarios, type UsuarioOption } from "@/services/usuarios"
import type { AuditLog } from "@/types/auditoria"

const PAGE_SIZE_INICIAL = 20

/**
 * El log de auditoría. Solo lectura: el sistema escribe estos eventos, no el usuario.
 *
 * ⚠️ LA BARRA DE FILTROS PROPIA (`AuditFilters.tsx`) SE BORRÓ al migrar a `<FiltersBar panel>`.
 * Era la más rica del repo y no se perdió ningún filtro: los cinco controles siguen ahí, con
 * "Desde"/"Hasta" unificados en un `daterange`. El porqué completo está en `_camposAuditoria.ts`.
 */
export default function AuditoriaPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)
  const [usuarios, setUsuarios] = useState<UsuarioOption[]>([])
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const [entidad, setEntidad] = useState("")
  const [evento, setEvento] = useState("")
  const [usuarioId, setUsuarioId] = useState("")
  const [rango, setRango] = useState<RangoFechas>({ desde: "", hasta: "" })

  useEffect(() => {
    fetchUsuarios().then((r) => setUsuarios(r.items)).catch(() => {})
  }, [])

  const campos = construirCampos({
    entidad, setEntidad, evento, setEvento, usuarioId, setUsuarioId, usuarios,
    // 🔴 Cambiar un filtro vuelve a la página 1 (invariante 4 del bloque B): filtrar parado en la
    // 7 pediría una página que el resultado nuevo no tiene y la tabla saldría vacía.
    rango, setRango, onFiltroChange: () => setPage(1),
  })
  const chips = chipsDeCampos(campos)

  /*
   * 🔴 UN SOLO OBJETO DE FILTROS PARA EL LISTADO Y PARA EL EXPORT. `useMemo` sobre los valores
   * primitivos porque `load` lo lleva en sus dependencias: un objeto nuevo por render dispararía
   * un fetch por render.
   * ⚠️ `registro_id` no viaja: el backend lo acepta pero esta barra no lo ofrece — ver
   * `_camposAuditoria.ts`.
   */
  const filtros = useMemo<AuditoriaFiltros>(() => ({
    entidad: entidad || undefined,
    evento: evento || undefined,
    usuario_id: usuarioId || undefined,
    fecha_desde: rango.desde || undefined,
    fecha_hasta: rango.hasta || undefined,
  }), [entidad, evento, usuarioId, rango.desde, rango.hasta])

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchAuditoria({ ...filtros, page, page_size: pageSize })
      setLogs(data.items)
      // El total sale del wrapper del backend, NUNCA de `data.items.length`.
      setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, filtros])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <PageHeader
        title="Auditoría"
        /* El conteo sale de `total` (el del filtro entero, del backend) y no del largo de la
           página. El subtítulo dice además que esta pantalla es de solo lectura. */
        description={
          loading && total === 0
            ? "Registro de cambios realizados en el sistema"
            : `${total} registro${total !== 1 ? "s" : ""} · los escribe el sistema, no se cargan a mano`
        }
        action={
          !loading && !error && logs.length > 0 ? (
            <ExportMenu onExport={(f) => exportarAuditoria(f, filtros)} />
          ) : undefined
        }
      />

      {/* `panel`: la forma completa del patrón de filtros (caja propia, "Más filtros" y los chips
          de la fila inferior). `disabled` durante la carga: los controles quedan A LA VISTA con
          sus chips pero no se pueden tocar (§3). */}
      <FiltersBar campos={campos} panel disabled={loading} />

      <AuditTable
        logs={logs}
        loading={loading}
        error={error}
        onRetry={load}
        onVerDetalle={setSelectedLog}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
      />

      {/*
       * 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS y sólo después de cargar. Antes la barra se
       * renderizaba dentro del bloque `logs.length > 0`, que a su vez colgaba de `!loading`: al
       * mover los estados adentro de la tabla esa protección desaparece, así que la guarda pasa a
       * ser explícita. El total que muestra es el TOTAL FILTRADO del backend, no `logs.length`.
       */}
      {!loading && !error && logs.length > 0 && (
        <Pagination page={page} total={total} pageSize={pageSize} onPageSizeChange={setPageSize} onPageChange={setPage} />
      )}

      <AuditDetailModal log={selectedLog} onClose={() => setSelectedLog(null)} />
    </div>
  )
}
