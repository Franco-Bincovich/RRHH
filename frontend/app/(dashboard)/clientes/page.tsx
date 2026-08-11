"use client"

import { useCallback, useEffect, useState } from "react"
import { Handshake, Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { ClienteModal } from "@/components/features/clientes/ClienteModal"
import { ClientesTabla } from "@/components/features/clientes/ClientesTabla"
import { cargarClientes } from "@/components/features/clientes/cargarClientes"
import { deleteCliente, exportarClientes } from "@/services/clientes"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Cliente } from "@/types/cliente"

/**
 * Catálogo de clientes. ORQUESTADOR: estado y navegación; la tabla y el formulario viven en
 * `components/features/clientes/`, y la carga en `cargarClientes.ts` (testeable sin jsdom).
 *
 * El corte es a propósito: el molde de este módulo es `areas/page.tsx`, que está en 271/150 por
 * tener todo junto. Se copió su estructura, no su tamaño.
 */
export default function ClientesPage() {
  const canWrite = useCanWrite()
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [incluirInactivos, setIncluirInactivos] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editando, setEditando] = useState<Cliente | undefined>(undefined)
  const [aBaja, setABaja] = useState<Cliente | null>(null)
  const [bajando, setBajando] = useState(false)

  const filtros = { incluirInactivos }
  const load = useCallback(
    () => cargarClientes({ incluirInactivos }, { setClientes, setLoading, setError }),
    [incluirInactivos],
  )
  useEffect(() => { void load() }, [load])

  function abrirAlta() { setEditando(undefined); setModalOpen(true) }
  function abrirEdicion(c: Cliente) { setEditando(c); setModalOpen(true) }

  async function confirmarBaja() {
    if (!aBaja) return
    setBajando(true)
    try {
      await deleteCliente(aBaja.id)
      setABaja(null)
      void load()
    } catch {
      toast.error("No se pudo dar de baja el cliente. Intentá de nuevo.")
    } finally {
      setBajando(false)
    }
  }

  if (loading) {
    return (
      <div>
        <PageHeader title="Clientes" description="Cargando..." />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Clientes" />
        <ErrorState description={error} action={load} />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Clientes"
        description={`${clientes.length} cliente${clientes.length !== 1 ? "s" : ""}`}
        action={
          <div className="flex items-center gap-2">
            <Button variant="outline" className="min-h-11"
                    onClick={() => setIncluirInactivos((v) => !v)}>
              {incluirInactivos ? "Ocultar bajas" : "Ver bajas"}
            </Button>
            {/* El MISMO filtro que el listado: el archivo no puede traer filas que la pantalla
                no muestre. El catálogo es GLOBAL (mig 108): no se acota por empresa por ningún
                lado, ni por query param ni por el header X-Empresa-Id. */}
            <ExportMenu onExport={(formato) => exportarClientes(formato, filtros)} />
            {canWrite && (
              <Button className="min-h-11" onClick={abrirAlta}>
                <Plus />
                Nuevo cliente
              </Button>
            )}
          </div>
        }
      />

      {clientes.length === 0 ? (
        <EmptyState
          icon={<Handshake />}
          title="Sin clientes"
          description="Todavía no hay clientes cargados. Creá el primero."
          action={canWrite ? (
            <Button className="min-h-11" onClick={abrirAlta}><Plus />Nuevo cliente</Button>
          ) : undefined}
        />
      ) : (
        <ClientesTabla clientes={clientes} canWrite={canWrite}
                       onEdit={abrirEdicion} onDelete={setABaja} />
      )}

      <ClienteModal
        open={modalOpen}
        cliente={editando}
        onClose={() => setModalOpen(false)}
        onSuccess={() => { setModalOpen(false); void load() }}
      />

      <ConfirmDialog
        open={Boolean(aBaja)}
        onClose={() => setABaja(null)}
        onConfirm={confirmarBaja}
        loading={bajando}
        title="Dar de baja el cliente"
        description={`"${aBaja?.nombre}" deja de aparecer al cargar horas. Las horas ya cargadas contra él no se tocan, y podés reactivarlo después.`}
        confirmLabel="Dar de baja"
      />
    </div>
  )
}
