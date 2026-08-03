"use client"

import { useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"

import { ApiError, clearSession, getSession, saveSession } from "@/services/api"
import { fetchUsuarioVigente, rolDesactualizado } from "@/services/auth"
import { primeraRutaPermitida, puede, seccionDeRuta } from "@/services/permisos"

/**
 * Guard de cliente para el dashboard. Solo UX — el backend es la autoridad (403).
 * Sin sesión → /login. Con contraseña temporal pendiente (`must_change_password`) →
 * /cambiar-password (bloquea todo el dashboard hasta cambiarla). Con sesión pero sin
 * permiso de lectura sobre la sección de la ruta actual → primera ruta que el rol sí
 * puede leer (dashboard para admin/gerencia). Si el rol no puede leer ninguna sección →
 * /login con la sesión limpiada (fail-closed). Rutas no gateadas (dashboard, config) pasan.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    const session = getSession()
    if (!session) {
      router.replace("/login")
      return
    }
    // Cambio de contraseña forzado: tiene prioridad sobre el gating por sección.
    if (session.user.must_change_password) {
      router.replace("/cambiar-password")
      return
    }
    const seccion = seccionDeRuta(pathname)
    if (seccion && !puede(session.user.rol, seccion, "read")) {
      const destino = primeraRutaPermitida(session.user.rol)
      if (destino) {
        router.replace(destino)
      } else {
        clearSession()
        router.replace("/login")
      }
    }
  }, [router, pathname])

  // Segundo efecto, a propósito separado del de arriba: aquel gatea con lo que hay guardado y
  // corre síncrono; este PREGUNTA. El de arriba no puede esperar a la red — dejaría ver por un
  // instante una pantalla que el rol no tiene permitida.
  useEffect(() => {
    const session = getSession()
    if (!session) return
    let cancelado = false

    fetchUsuarioVigente()
      .then((vigente) => {
        if (cancelado || !rolDesactualizado(session.user.rol, vigente.rol)) return
        saveSession({ ...session, user: { ...session.user, rol: vigente.rol! } })
        // Recarga entera y no un setState: el rol lo leen al montar el sidebar, el menú de
        // usuario y cada botón de escritura. Refrescar solo este componente dejaría la mitad
        // de la pantalla mostrando permisos viejos, que es el bug que esto viene a cerrar.
        // No hay loop: después de recargar, el guardado y el vigente ya coinciden.
        window.location.reload()
      })
      .catch((e) => {
        // 403 = USUARIO_INACTIVO (el 401 lo maneja el interceptor de refresh). La sesión ya no
        // vale para nada: se limpia acá en vez de dejarlo dando vueltas por una app que le
        // responde 403 en cada pantalla.
        if (e instanceof ApiError && e.status === 403) {
          clearSession()
          router.replace("/login")
        }
      })

    return () => { cancelado = true }
  }, [router, pathname])

  return <>{children}</>
}
