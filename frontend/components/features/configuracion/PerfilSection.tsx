"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Lock, LogOut, UserCircle } from "lucide-react"

import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { CambiarPasswordForm } from "@/components/features/usuarios/CambiarPasswordForm"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { getSession } from "@/services/api"
import { logout } from "@/services/auth"
import { ROL_LABEL, type Session } from "@/types/auth"

/**
 * Cambio de contraseña + datos del usuario logueado.
 *
 * Estas dos secciones NO se gatean por rol: todo usuario necesita poder cambiar su propia
 * contraseña y cerrar sesión, sea cual sea su rol. Son sobre uno mismo, no sobre la empresa.
 */
export function PerfilSection() {
  const router = useRouter()
  const [session, setSession] = useState<Session | null>(null)

  // getSession() lee localStorage: en el primer render del servidor no existe.
  useEffect(() => setSession(getSession()), [])

  const cerrarSesion = async () => {
    await logout() // revoca en Supabase y limpia la sesión local (best-effort)
    router.push("/login")
  }

  return (
    <>
      <ConfigSection
        value="password"
        icon={<Lock className="size-5 text-primary" />}
        title="Cambiar contraseña"
      >
        <CambiarPasswordForm forced={false} />
      </ConfigSection>

      <ConfigSection
        value="perfil"
        icon={<UserCircle className="size-5 text-primary" />}
        title="Mi perfil"
      >
        {session ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs text-muted-foreground">Nombre</p>
                <p className="mt-0.5 font-medium">
                  {session.user.nombre} {session.user.apellido}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Email</p>
                <p className="mt-0.5 font-medium">{session.user.email}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Rol</p>
                <p className="mt-0.5 font-medium">
                  {ROL_LABEL[session.user.rol] ?? session.user.rol}
                </p>
              </div>
            </div>
            <Separator />
            <Button variant="destructive" onClick={cerrarSesion}>
              <LogOut className="mr-2 size-4" />
              Cerrar sesión
            </Button>
          </div>
        ) : (
          <Button variant="destructive" onClick={cerrarSesion}>
            <LogOut className="mr-2 size-4" />
            Cerrar sesión
          </Button>
        )}
      </ConfigSection>
    </>
  )
}
