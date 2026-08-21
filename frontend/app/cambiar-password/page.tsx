"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

import { EsqueletoAuth, MarcaAuth, MarcoAuth } from "@/components/features/auth/MarcaAuth"
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

  /*
   * 🔴 EL RETURN TEMPRANO SE QUEDA, Y LO QUE CAMBIÓ ES LO QUE DEVUELVE. Protege dos cosas: que
   * `forced` no se calcule antes de haber leído la sesión, y que alguien sin sesión no vea el
   * formulario mientras la redirección a `/login` ocurre. Antes devolvía `null` —una pantalla
   * blanca— y ahora devuelve el esqueleto de la pantalla que viene. Sacarlo para "simplificar" se
   * lleva las dos protecciones.
   */
  if (estado === "cargando") return <EsqueletoAuth />

  const forced = estado === "forzado"

  return (
    <MarcoAuth>
      <MarcaAuth titulo="Cambiar contraseña">
        {forced
          ? "Tenés que cambiar tu contraseña temporal antes de continuar."
          : "Actualizá la contraseña de tu cuenta."}
      </MarcaAuth>
      <div className="rounded-2xl border bg-card p-6 shadow-sm">
        <CambiarPasswordForm forced={forced} />
      </div>
    </MarcoAuth>
  )
}
