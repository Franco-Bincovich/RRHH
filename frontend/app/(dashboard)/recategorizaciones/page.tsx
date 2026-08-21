"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { Label } from "@/components/ui/label"
import { Pagination } from "@/components/ui/Pagination"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { EmpleadoCombobox } from "@/components/features/shared/EmpleadoCombobox"
import { RecategorizacionModal } from "@/components/features/recategorizaciones/RecategorizacionModal"
import { RecategorizacionesTabla } from "@/components/features/recategorizaciones/RecategorizacionesTabla"
import { cargarRecategorizaciones } from "@/components/features/recategorizaciones/cargarRecategorizaciones"
import { useFiltrosRecategorizaciones } from "@/components/features/recategorizaciones/useFiltrosRecategorizaciones"
import { exportarRecategorizaciones } from "@/services/recategorizaciones"
import { useCanRead, useCanWrite } from "@/hooks/useCanWrite"
import type { Recategorizacion } from "@/types/recategorizacion"

const PAGE_SIZE = 20

/**
 * La planilla de RECATEGORIZACIONES: el registro de cambios de rol, seniority o categoría.
 * ORQUESTADOR — el estado y la navegación; la tabla, el formulario y la carga viven en
 * `components/features/recategorizaciones/`.
 *
 * 🔴 ES REGISTRO PURO, Y LA PANTALLA NO PUEDE INSINUAR LO CONTRARIO. El sistema de diseño (§7)
 * advierte que un prototipo anterior prometió **flujo de aprobación** e **impacto porcentual**, y
 * ninguno de los dos existe. Por eso acá no hay estado, ni "pendiente", ni botón de aprobar, ni
 * un solo `%`: se carga y queda cargado, y el subtítulo lo dice antes de que nadie lo suponga.
 *
 * 🔴 Y NO HAY BORRAR EN NINGUNA SUPERFICIE: el backend no publica DELETE porque borrar rompe la
 * cadena de valores anteriores. La corrección es editar.
 */
export default function RecategorizacionesPage() {
  const canWrite = useCanWrite()
  // El impacto salarial es un dato de COSTOS aunque la pantalla sea de recategorizaciones: sin
  // ese permiso la columna NO se dibuja vacía, no se dibuja. Ver `_columnas.ts`.
  const mostrarImpacto = useCanRead("costos")

  const [items, setItems] = useState<Recategorizacion[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editando, setEditando] = useState<Recategorizacion | undefined>(undefined)

  const { filtros, campos, chips, empleado, elegirEmpleado } =
    useFiltrosRecategorizaciones(() => setPage(1))

  const load = useCallback(
    () => cargarRecategorizaciones(filtros, page, PAGE_SIZE,
                                   { setItems, setTotal, setLoading, setError }),
    [filtros, page],
  )
  useEffect(() => { void load() }, [load])

  function abrirAlta() { setEditando(undefined); setModalOpen(true) }

  return (
    <div>
      <PageHeader
        title="Recategorizaciones"
        // El conteo sale de `total` —el real del filtro—, no de `items.length`, que es una página.
        description={`${total} ${total === 1 ? "recategorización registrada" : "recategorizaciones registradas"} · Es un registro histórico: se carga y queda registrado, no hay circuito de aprobación.`}
        action={
          <div className="flex items-center gap-2">
            {/* Los MISMOS filtros que el listado: el archivo no puede traer filas que la
                pantalla no muestre. La columna de impacto la saca el backend según el permiso. */}
            <ExportMenu onExport={(formato) => exportarRecategorizaciones(formato, filtros)} />
            {canWrite && (
              <Button className="min-h-11" onClick={abrirAlta}>
                <Plus />
                Registrar recategorización
              </Button>
            )}
          </div>
        }
      />

      <div className="mb-4 grid grid-cols-1 items-end gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="filtro-empleado">Colaborador</Label>
          {/* Fuera de `FiltersBar` a propósito: es el combobox con búsqueda server-side, no un
              select plano. El porqué está en `useFiltrosRecategorizaciones`. */}
          <EmpleadoCombobox
            id="filtro-empleado"
            value={empleado?.id ?? ""}
            onChange={elegirEmpleado}
            disabled={loading}
          />
        </div>
        <FiltersBar campos={campos} disabled={loading} />
      </div>

      <RecategorizacionesTabla
        items={items}
        loading={loading}
        error={error}
        mostrarImpacto={mostrarImpacto}
        canWrite={canWrite}
        chips={chips}
        onRetry={load}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        onEditar={(r) => { setEditando(r); setModalOpen(true) }}
        // Con un colaborador filtrado, él es el sujeto de la frase del vacío ("Juan Pérez no
        // tiene recategorizaciones…"); sin filtro queda impersonal, porque la empresa —que es el
        // sujeto en las otras pantallas— acá no es un filtro.
        sujetoVacio={empleado ? "Colaborador" : undefined}
        accionVacio={canWrite ? (
          <Button className="min-h-11" onClick={abrirAlta}><Plus />Registrar la primera</Button>
        ) : undefined}
      />

      {!loading && !error && items.length > 0 && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}

      {canWrite && (
        <RecategorizacionModal
          open={modalOpen}
          original={editando}
          mostrarImpacto={mostrarImpacto}
          onClose={() => setModalOpen(false)}
          onSuccess={() => { setModalOpen(false); void load() }}
        />
      )}
    </div>
  )
}
