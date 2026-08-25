"use client"

import { useEffect, useState } from "react"
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
  eliminarUsuario, exportarUsuarios, fetchUsuarios,
  type CrearUsuarioResult, type UsuarioOption,
} from "@/services/usuarios"
import { getRol, puede } from "@/services/permisos"
import type { UserRol } from "@/types/auth"

/**
 * 🔴 EL GATE DE ESTA PANTALLA ERA UN TERCERO Y CONTRADECÍA A LOS OTROS DOS. Hasta el 25/8/2026
 * acá vivía un guard admin-only (`puede(rol, "usuarios", "write")` + `router.replace`) que
 * rebotaba a `gerencia_lectura`, contra lo que dicen los tres lugares donde el modelo está
 * escrito: `utils/permisos.py`, `services/permisos.ts` y `routers/usuarios.py`, que gatea el
 * listado con `USUARIOS + READ`. **Rige el modelo y el guard se fue**, por tres razones: (1)
 * `gerencia_lectura` es "lectura en todo, escritura en nada" y esa excepción no la decidió nadie;
 * (2) no protegía nada —el backend ya le sirve `GET /api/usuarios` a ese rol—; (3) la escritura
 * sigue gateada aparte, con `esAdmin`. Quién ENTRA lo decide el AuthGuard, como en todas las
 * demás. Lo vigila `components/layout/gatesDePagina.test.ts`.
 */
export default function UsuariosPage() {
  const [rol, setRol] = useState<UserRol | null>(null)
  const [checked, setChecked] = useState(false)
  const [usuarios, setUsuarios] = useState<UsuarioOption[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [creado, setCreado] = useState<CrearUsuarioResult | null>(null)
  const [aEliminar, setAEliminar] = useState<UsuarioOption | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // Sólo para la ESCRITURA (alta y baja). Entrar a mirar lo decide el AuthGuard — ver arriba.
  const esAdmin = rol !== null && puede(rol, "usuarios", "write")

  useEffect(() => {
    setRol(getRol())
    setChecked(true)
  }, [])

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

  // 🔑 Carga para TODO el que llegó, no sólo para el admin: `gerencia_lectura` viene a leer.
  useEffect(() => {
    if (checked) void load()
  }, [checked])

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

  // Sólo se espera a saber el rol. El rebote se fue: quién entra lo decide el AuthGuard.
  if (!checked) return null

  // `null` sin permiso de escritura: el mismo criterio que `useCanWrite` en el resto del
  // producto — una acción que siempre terminaría en 403 no se ofrece.
  const crearBtn = esAdmin ? (
    <Button className="min-h-11" onClick={() => setModalOpen(true)}>
      <Plus />
      Crear usuario
    </Button>
  ) : null

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
        onDelete={esAdmin ? setAEliminar : undefined}
        deletingId={deletingId}
        accionVacio={crearBtn ?? undefined}
      />

      <CrearUsuarioModal
        open={modalOpen} onClose={() => setModalOpen(false)}
        onCreated={(r) => { setModalOpen(false); setCreado(r) }}
      />

      <PasswordRevealModal
        open={creado !== null} username={creado?.username ?? ""}
        password={creado?.password_temporal ?? ""}
        onClose={() => { setCreado(null); void load() }}
      />

      {aEliminar && (
        <ConfirmDialog
          open onClose={() => setAEliminar(null)} onConfirm={confirmarEliminar}
          title="Eliminar usuario" confirmLabel="Sí, eliminar"
          description={`Vas a eliminar el usuario ${aEliminar.nombre} ${aEliminar.apellido}. No se puede deshacer.`}
          loading={deletingId === aEliminar.id}
        />
      )}
    </div>
  )
}
