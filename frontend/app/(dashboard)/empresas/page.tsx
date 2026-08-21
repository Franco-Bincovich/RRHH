"use client"

import { useState, useEffect } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { EmpresaModal } from "@/components/features/empresas/EmpresaModal"
import { EmpresasTable } from "@/components/features/empresas/EmpresasTable"
import { AVISO_CATALOGO_GLOBAL } from "@/components/features/empresas/_avisoGlobal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarEmpresas, fetchEmpresas, toggleEmpresaActiva } from "@/services/empresas"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Empresa } from "@/types/empresa"

/**
 * El listado de empresas del grupo.
 *
 * 🔴 NO TIENE FILTROS NI PIE, y no le faltan: `GET /api/empresas` no acepta un solo Query y
 * devuelve la lista entera. Sin filtros no hay chips que mostrar y sin `page`/`total` del backend
 * no hay pie que armar — ponerle chips a una pantalla que no filtra sería inventar filtros que el
 * backend no puede honrar. Lo que sí toma del patrón es la tabla: `patron="datos"`, los anchos
 * declarados, el esqueleto con la misma grilla y el vacío adentro de la tabla.
 *
 * 🔴 Y EL SELECTOR DE EMPRESA DEL SIDEBAR NO LA ACOTA: acá la empresa ES el recurso. Como es lo
 * contrario a lo que hace el resto del producto, la pantalla lo dice en el subtítulo
 * (`_avisoGlobal.ts`).
 */
export default function EmpresasPage() {
  const canWrite = useCanWrite()
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Empresa | undefined>(undefined)
  const [togglingId, setTogglingId] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchEmpresas()
      setEmpresas(data.items)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  function openCreate() {
    setEditing(undefined)
    setModalOpen(true)
  }

  function openEdit(empresa: Empresa) {
    setEditing(empresa)
    setModalOpen(true)
  }

  async function handleToggle(empresa: Empresa) {
    setTogglingId(empresa.id)
    try {
      await toggleEmpresaActiva(empresa.id, !empresa.activa)
      void load()
    } catch {
      toast.error("No se pudo cambiar el estado de la empresa. Intentá de nuevo.")
    } finally {
      setTogglingId(null)
    }
  }

  const crearBtn = (
    <Button className="min-h-11" onClick={openCreate}>
      <Plus />
      Nueva empresa
    </Button>
  )

  return (
    <div>
      <PageHeader
        title="Empresas"
        /* El conteo y, pegado, la advertencia de que el sidebar no filtra acá. Va en el
           SUBTÍTULO porque describe lo que la pantalla ES — misma regla que en clientes.
           `empresas.length` como conteo es correcto ACÁ Y SÓLO ACÁ: el endpoint devuelve todo,
           así que el largo del array ES el total. En un listado paginado ese mismo `.length` es
           el bug que `paginacionTotales.test.ts` persigue. */
        description={
          loading
            ? "Cargando..."
            : `${empresas.length} empresa${empresas.length !== 1 ? "s" : ""} · ${AVISO_CATALOGO_GLOBAL}`
        }
        action={
          <div className="flex items-center gap-2">
            {/* El archivo sale del MISMO listado que la tabla y esta pantalla no tiene
                filtros: trae exactamente las empresas que se ven, activas e inactivas.
                Disponible también para gerencia_lectura — exportar es una lectura. */}
            {!loading && !error && empresas.length > 0 && <ExportMenu onExport={exportarEmpresas} />}
            {canWrite && crearBtn}
          </div>
        }
      />

      <EmpresasTable
        empresas={empresas}
        loading={loading}
        error={error}
        canWrite={canWrite}
        onRetry={load}
        onEdit={openEdit}
        onToggle={handleToggle}
        togglingId={togglingId}
        accionVacio={canWrite ? crearBtn : undefined}
      />

      <EmpresaModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={() => { setModalOpen(false); void load() }}
        empresa={editing}
      />
    </div>
  )
}
