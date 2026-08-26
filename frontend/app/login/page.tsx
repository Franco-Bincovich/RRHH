"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

import { EsqueletoAuth, MarcaAuth, MarcoAuth } from "@/components/features/auth/MarcaAuth"
import { LoginForm } from "@/components/features/auth/LoginForm"
import { getSession } from "@/services/api"
import { MARCA } from "@/lib/marca"

export default function LoginPage() {
  const router = useRouter()
  const [comprobando, setComprobando] = useState(true)

  /*
   * Si ya hay sesión al montar, saltar el login. `getSession` lee de `localStorage`, que no existe
   * en el servidor, así que el chequeo va en un efecto y **hay un instante sin respuesta**.
   *
   * 🔴 ESE INSTANTE AHORA DIBUJA UN ESQUELETO Y ANTES DIBUJABA EL FORMULARIO ENTERO. Con sesión
   * válida —el caso más común: alguien que vuelve a la pestaña— la pantalla mostraba el login
   * completo y lo reemplazaba de un salto por el dashboard. Se leía como un cierre de sesión que
   * no ocurrió, y en una conexión lenta daba tiempo a empezar a tipear el usuario.
   *
   * ⚠️ El `setComprobando(false)` va SOLO en la rama sin sesión: con sesión no se apaga a
   * propósito, para que el esqueleto siga hasta que la navegación ocurra. Apagarlo en las dos
   * ramas devolvería el parpadeo del formulario que este estado vino a sacar.
   */
  useEffect(() => {
    if (getSession()) router.replace("/dashboard")
    else setComprobando(false)
  }, [router])

  if (comprobando) return <EsqueletoAuth />

  return (
    <MarcoAuth pie="¿Problemas para ingresar? Contactá a Capital Humano.">
      <MarcaAuth titulo={MARCA}>Ingresá a tu cuenta</MarcaAuth>
      <div className="rounded-2xl border bg-card p-6 shadow-sm">
        <LoginForm />
      </div>
    </MarcoAuth>
  )
}
