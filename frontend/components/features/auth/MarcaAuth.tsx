import { Building2 } from "lucide-react"
import type { ReactNode } from "react"

import { Skeleton } from "@/components/ui/skeleton"

/**
 * El encabezado de las pantallas de acceso: el cuadrado con el isotipo, el nombre del producto y
 * una línea que dice qué hay que hacer acá.
 *
 * 🔴 POR QUÉ ES UN COMPONENTE Y NO MARKUP REPETIDO. Estaba escrito **idéntico** en `/login` y en
 * `/cambiar-password`, hasta el `rounded-2xl` y el `shadow-lg`. Son las dos pantallas que un
 * usuario ve una detrás de la otra la primera vez que entra —login, y de ahí directo al cambio de
 * la contraseña temporal—, así que cualquier diferencia entre las dos copias se lee como que el
 * sistema cambió de identidad en el medio del flujo.
 *
 * 🔴 EL ÍCONO VA CON `text-primary-foreground` Y NUNCA CON `text-white`. En el tema oscuro
 * `--primary` se aclara a #7DA9FB y `--primary-foreground` deja de ser blanco: pasa a ser el
 * fondo de la página (#0B1220). Un blanco hardcodeado ahí da 3.68:1 y `app/contrasteTokens.test.ts`
 * no lo puede ver, porque ese test mide los TOKENS y no lo que cada pantalla escribe a mano. Con
 * el token da 7.97:1. El porqué completo está en `app/paleta.css`, en el bloque `.dark`.
 */
export function MarcaAuth({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className="mb-8 flex flex-col items-center gap-3">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-primary shadow-lg">
        <Building2 className="size-7 text-primary-foreground" aria-hidden="true" />
      </div>
      <div className="text-center">
        <h1 className="text-xl font-bold tracking-tight text-foreground">{titulo}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{children}</p>
      </div>
    </div>
  )
}

/**
 * El marco de las dos pantallas de acceso: centrado vertical, ancho máximo de una columna, y la
 * tarjeta con el formulario adentro.
 *
 * Vive al lado de `MarcaAuth` porque las dos pantallas lo repetían igual de literal (el mismo
 * `flex min-h-screen items-center justify-center`, el mismo `max-w-sm`, la misma tarjeta
 * `rounded-2xl border bg-card p-6 shadow-sm`), y separarlo dejaría medio encabezado compartido y
 * medio no.
 */
export function MarcoAuth({ children, pie }: { children: ReactNode; pie?: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-sm">
        {children}
        {pie && <p className="mt-6 text-center text-xs text-muted-foreground">{pie}</p>}
      </div>
    </div>
  )
}

/**
 * El esqueleto de las dos pantallas de acceso, mientras se lee la sesión de `localStorage`.
 *
 * 🔴 REEMPLAZA A UNA PANTALLA EN BLANCO, que es lo que las dos hacían: `/cambiar-password`
 * devolvía `return null` y `/login` dibujaba el formulario completo para después borrarlo de un
 * salto si ya había sesión. Las dos leen la sesión en un `useEffect` —`localStorage` no existe en
 * el servidor—, así que ese instante existe siempre y no se puede evitar; lo que sí se puede es
 * que tenga la forma de lo que viene (§3, "esqueleto con la grilla exacta") en vez de nada.
 *
 * El shimmer de 1,2s es el del sistema de diseño, no el `animate-pulse` de 2s del componente.
 */
export function EsqueletoAuth() {
  return (
    <MarcoAuth>
      <div className="mb-8 flex flex-col items-center gap-3">
        <Skeleton shimmer className="size-14 rounded-2xl" />
        <Skeleton shimmer className="h-6 w-40 rounded-md" />
        <Skeleton shimmer className="h-4 w-52 rounded-md" />
      </div>
      <Skeleton shimmer className="h-[19rem] w-full rounded-2xl" />
    </MarcoAuth>
  )
}
