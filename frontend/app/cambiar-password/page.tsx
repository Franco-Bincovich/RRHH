"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Building2 } from "lucide-react"

import { CambiarPasswordForm } from "@/components/features/usuarios/CambiarPasswordForm"
import { getSession } from "@/services/api"

export default function CambiarPasswordPage() {
  const router = useRouter()
  const [estado, setEstado] = useState<"cargando" | "forzado" | "voluntario">("cargando")

  // Sesión leída tras montar (localStorage). Sin sesión → /login. El flag define el modo.
  useEffect(() => {
    const session = getSession()
    if (!session) {
      router.replace("/login")
      return
    }
    setEstado(session.user.must_change_password ? "forzado" : "voluntario")
  }, [router])

  if (estado === "cargando") return null

  const forced = estado === "forzado"

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary shadow-lg">
            <Building2 className="size-7 text-primary-foreground" />
          </div>
          <div className="text-center">
            <h1 className="text-xl font-bold tracking-tight text-foreground">Cambiar contraseña</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {forced
                ? "Tenés que cambiar tu contraseña temporal antes de continuar."
                : "Actualizá la contraseña de tu cuenta."}
            </p>
          </div>
        </div>

        <div className="rounded-2xl border bg-card p-6 shadow-sm">
          <CambiarPasswordForm forced={forced} />
        </div>
      </div>
    </div>
  )
}
