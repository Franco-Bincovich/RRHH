"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Plus, Users } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { UsuariosTable } from "@/components/features/usuarios/UsuariosTable"
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
        description={loading ? "Cargando..." : `${usuarios.length} usuario${usuarios.length !== 1 ? "s" : ""}`}
        action={!loading && !error && usuarios.length > 0 ? (
          // El archivo sale del MISMO listado que la tabla y esta pantalla no tiene filtros:
          // trae exactamente lo que se ve. Sin filas no se ofrece exportar.
          <div className="flex items-center gap-2">
            <ExportMenu onExport={exportarUsuarios} />
            {crearBtn}
          </div>
        ) : undefined}
      />

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
        </div>
      ) : error ? (
        <ErrorState description="No se pudieron cargar los usuarios." action={load} />
      ) : usuarios.length === 0 ? (
        <EmptyState
          icon={<Users />}
          title="Sin usuarios"
          description="Todavía no hay usuarios del sistema. Creá el primero."
          action={crearBtn}
        />
      ) : (
        <UsuariosTable usuarios={usuarios} onDelete={setAEliminar} deletingId={deletingId} />
      )}

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
