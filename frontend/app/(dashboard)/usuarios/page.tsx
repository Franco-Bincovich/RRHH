"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { UsuariosTable } from "@/components/features/usuarios/UsuariosTable"
import { AVISO_CATALOGO_GLOBAL } from "@/components/features/usuarios/_avisos"
import { CrearUsuarioModal } from "@/components/features/usuarios/CrearUsuarioModal"
import { PasswordRevealModal } from "@/components/features/usuarios/PasswordRevealModal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import {
  eliminarUsuario,
  exportarUsuarios,
  fetchUsuarios,
  type CrearUsuarioResult,
  type UsuarioOption,
} from "@/services/usuarios"
import { getRol, primeraRutaPermitida, puede } from "@/services/permisos"
import type { UserRol } from "@/types/auth"

export default function UsuariosPage() {
  const router = useRouter()
  const [rol, setRol] = useState<UserRol | null>(null)
  const [checked, setChecked] = useState(false)
  const [usuarios, setUsuarios] = useState<UsuarioOption[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [creado, setCreado] = useState<CrearUsuarioResult | null>(null)
  const [aEliminar, setAEliminar] = useState<UsuarioOption | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const esAdmin = rol !== null && puede(rol, "usuarios", "write")

  // Guard admin-only en cliente (el backend es la autoridad real, 403). No-admin → redirect.
  useEffect(() => {
    const r = getRol()
    setRol(r)
    setChecked(true)
    if (r !== null && !puede(r, "usuarios", "write")) {
      router.replace(primeraRutaPermitida(r) ?? "/dashboard")
    }
  }, [router])

  async function load() {
    setLoading(true)
    setError(false)
    try {
      setUsuarios((await fetchUsuarios()).items)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (esAdmin) void load()
  }, [esAdmin])

  async function confirmarEliminar() {
    if (!aEliminar) return
    setDeletingId(aEliminar.id)
    try {
      await eliminarUsuario(aEliminar.id)
      setAEliminar(null)
      void load()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "No se pudo eliminar el usuario.")
    } finally {
      setDeletingId(null)
    }
  }

  if (!checked || !esAdmin) return null

  const crearBtn = (
    <Button className="min-h-11" onClick={() => setModalOpen(true)}>
      <Plus />
      Crear usuario
    </Button>
  )

  return (
    <div>
      <PageHeader
        title="Usuarios"
        /* El conteo y, pegado, el aviso de que esta pantalla no se recorta por empresa. Va en el
           SUBTÍTULO porque describe lo que la pantalla ES — misma regla que en clientes.
           `usuarios.length` como conteo es correcto ACÁ Y SÓLO ACÁ: el endpoint devuelve todo,
           así que el largo del array ES el total. En un listado paginado ese mismo `.length` es
           el bug que `paginacionTotales.test.ts` persigue. */
        description={
          loading
            ? "Cargando..."
            : `${usuarios.length} usuario${usuarios.length !== 1 ? "s" : ""} · ${AVISO_CATALOGO_GLOBAL}`
        }
        action={
          // El archivo sale del MISMO listado que la tabla y esta pantalla no tiene filtros:
          // trae exactamente lo que se ve. Sin filas no se ofrece exportar.
          <div className="flex items-center gap-2">
            {!loading && !error && usuarios.length > 0 && <ExportMenu onExport={exportarUsuarios} />}
            {crearBtn}
          </div>
        }
      />

      <UsuariosTable
        usuarios={usuarios}
        loading={loading}
        error={error}
        onRetry={load}
        onDelete={setAEliminar}
        deletingId={deletingId}
        accionVacio={crearBtn}
      />

      <CrearUsuarioModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={(r) => { setModalOpen(false); setCreado(r) }}
      />

      <PasswordRevealModal
        open={creado !== null}
        username={creado?.username ?? ""}
        password={creado?.password_temporal ?? ""}
        onClose={() => { setCreado(null); void load() }}
      />

      {aEliminar && (
        <ConfirmDialog
          open
          onClose={() => setAEliminar(null)}
          onConfirm={confirmarEliminar}
          title="Eliminar usuario"
          description={`Vas a eliminar el usuario ${aEliminar.nombre} ${aEliminar.apellido}. No se puede deshacer.`}
          confirmLabel="Sí, eliminar"
          loading={deletingId === aEliminar.id}
        />
      )}
    </div>
  )
}
