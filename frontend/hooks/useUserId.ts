import { useEffect, useState } from "react"

import { getSession } from "@/services/session"

/**
 * Id del usuario logueado, resuelto DESPUÉS de montar.
 *
 * Mismo patrón —y mismo motivo— que useRol: `getSession()` lee de localStorage, que no existe
 * en SSR, así que llamarlo durante el render provoca hydration mismatch. Devuelve null en el
 * server y en el primer render del client (coinciden), y el id real tras el mount.
 *
 * `null` = "todavía no montó", NO "no hay usuario". Quien lo use para decidir permisos tiene
 * que tratar null como "no puedo todavía" — la barrera real está en el backend.
 */
export function useUserId(): string | null {
  const [id, setId] = useState<string | null>(null)
  useEffect(() => { setId(getSession()?.user.id ?? null) }, [])
  return id
}
