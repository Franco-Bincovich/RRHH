"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { ClienteModal } from "@/components/features/clientes/ClienteModal"
import { ClientesTabla } from "@/components/features/clientes/ClientesTabla"
import { cargarClientes } from "@/components/features/clientes/cargarClientes"
import { construirCampos } from "@/components/features/clientes/_camposClientes"
import { AVISO_CATALOGO_GLOBAL } from "@/components/features/clientes/_avisoGlobal"
import { deleteCliente, exportarClientes } from "@/services/clientes"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Cliente } from "@/types/cliente"

/**
 * Catálogo de clientes. ORQUESTADOR: estado y navegación; la tabla y el formulario viven en
 * `components/features/clientes/`, y la carga en `cargarClientes.ts` (testeable sin jsdom).
 *
 * 🔴 ES UN CATÁLOGO GLOBAL: el selector de empresa del sidebar NO lo acota (migraciones 108/109),
 * y como es lo contrario a lo que hace el resto del producto la pantalla lo DICE en el subtítulo
 * en vez de dejar que alguien lo deduzca al chocar con el 409 de nombre duplicado. Molde:
 * `/perfiles-puesto`, el otro catálogo del grupo.
 *
 * ⚠️ NO TIENE PIE DE PAGINACIÓN, y no le falta: `GET /api/clientes` no acepta `page` ni
 * `page_size` — devuelve el catálogo entero. Sin `total` del backend distinto del largo del
 * array, un pie sería aritmética del cliente sobre lo que ya tiene.
 */
export default function ClientesPage() {
  const canWrite = useCanWrite()
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [bajasFiltro, setBajasFiltro] = useState("")
  const [modalOpen, setModalOpen] = useState(false)
  const [editando, setEditando] = useState<Cliente | undefined>(undefined)
  const [aBaja, setABaja] = useState<Cliente | null>(null)
  const [bajando, setBajando] = useState(false)

  // El listado no pagina, así que no hay página que resetear; el molde se respeta igual para que
  // el día que el backend acepte `page` no haya que rehacer el cableado.
  const campos = construirCampos({ bajasFiltro, setBajasFiltro, onFiltroChange: () => {} })
  const chips = chipsDeCampos(campos)

  const incluirInactivos = bajasFiltro === "todos"
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

  return (
    <div>
      <PageHeader
        title="Clientes"
        /* El conteo y, pegado, la advertencia de que el sidebar no filtra acá. Va en el
           SUBTÍTULO y no en un bloque de aviso porque describe lo que la pantalla ES, no algo
           que va a pasar — misma regla que en /perfiles-puesto. */
        description={`${clientes.length} cliente${clientes.length !== 1 ? "s" : ""} · ${AVISO_CATALOGO_GLOBAL}`}
        action={
          <div className="flex items-center gap-2">
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

      {/* `panel`: la forma completa del patrón de filtros (caja propia y los chips de la fila
          inferior). Un solo control, así que no hay "Más filtros" — ver `_camposClientes.ts`. */}
      <FiltersBar campos={campos} panel disabled={loading} />

      <ClientesTabla
        clientes={clientes}
        loading={loading}
        error={error}
        canWrite={canWrite}
        onRetry={load}
        onEdit={abrirEdicion}
        onDelete={setABaja}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? (
          <Button className="min-h-11" onClick={abrirAlta}>Crear el primero</Button>
        ) : undefined}
      />

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
