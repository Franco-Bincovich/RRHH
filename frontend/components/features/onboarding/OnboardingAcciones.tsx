"use client"

import Link from "next/link"
import { Settings2 } from "lucide-react"
import type { ReactNode } from "react"

import { buttonVariants } from "@/components/ui/button"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarOnboardings } from "@/services/onboarding"
import { cn } from "@/lib/utils"

/**
 * Las acciones del encabezado de /onboarding: exportar, ir a los templates y empezar uno.
 *
 * Salieron de la página al migrarla al patrón del bloque B. Ese archivo estaba en **396 líneas
 * contra un límite de 150** —deuda anotada en CLAUDE.md— y los estados nuevos lo empujaban a 404;
 * entre este corte, `IniciarOnboardingModal` y `OnboardingList` quedó adentro del límite.
 *
 * ⚠️ LOS DOS CONTROLES DE LA DERECHA ERAN CONTROLES A MANO: un `<Link>` con las clases del botón
 * `outline` escritas de nuevo y un `<button>` con `bg-primary`, su propio `hover:` y su propio
 * `focus-visible:` — copias parciales de primitivos que el repo ya tiene, las dos con 40px de
 * alto en vez de los 44 que el repo usa para todo control táctil. El link sigue siendo un `<a>`
 * (navega, no ejecuta): lo que se unificó son las clases, vía `buttonVariants`.
 *
 * 🔴 EXPORTAR ES LECTURA y por eso no va detrás de `canWrite`: quien puede ver el listado puede
 * llevárselo. Lo que sí gatea el permiso es iniciar un proceso.
 */
export function OnboardingAcciones({ canWrite, iniciarBtn }: {
  canWrite: boolean
  iniciarBtn: ReactNode
}) {
  return (
    <div className="absolute right-0 top-0 flex items-center gap-2">
      {/* Exportar es LECTURA: no va detrás de canWrite. */}
      <ExportMenu onExport={exportarOnboardings} />
      {/* ⚠️ LOS DOS ERAN CONTROLES A MANO: un `<Link>` con las clases del botón `outline` y un
          `<button>` con `bg-primary` y su propio `hover:`/`focus-visible:` — copias parciales
          de primitivos que el repo ya tiene, las dos con 40px de alto en vez de los 44 que el
          repo usa para todo control táctil. El link sigue siendo un `<a>` (navega, no
          ejecuta): lo que se unificó son las clases, vía `buttonVariants`. */}
      <Link
        href="/onboarding/templates"
        className={cn(buttonVariants({ variant: "outline" }), "min-h-11 gap-1.5")}
      >
        <Settings2 className="size-4" />
        <span className="hidden sm:inline">Gestionar templates</span>
      </Link>
      {canWrite && iniciarBtn}
    </div>
  )
}
