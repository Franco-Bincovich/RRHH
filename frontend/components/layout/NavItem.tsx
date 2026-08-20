"use client"

import type { ElementType } from "react"
import Link from "next/link"

import { cn } from "@/lib/utils"

interface NavItemProps {
  href?: string
  label: string
  icon: ElementType
  isActive: boolean
  onClick?: () => void
  /** Sin pantalla todavía: se ve pero no navega ni entra en el recorrido con teclado. */
  proximamente?: boolean
}

const BASE = "flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors"

/** Link de navegación individual. Marca el activo con estilo + aria-current="page".
 *
 *  Un ítem `proximamente` NO se renderiza como <Link>: se renderiza como <span>, que no es
 *  focusable, así que el tabulado lo saltea igual que el `disabled` del <Tab> de empresas/[id].
 *  La alternativa —un <Link> a la ruta futura— sería un 404 con forma de menú, que es peor que
 *  una entrada que dice claramente que todavía no está. */
export function NavItem({ href, label, icon: Icon, isActive, onClick, proximamente }: NavItemProps) {
  if (proximamente || !href) {
    return (
      <span aria-disabled="true" className={cn(BASE, "cursor-not-allowed text-sidebar-foreground/45")}>
        <Icon className="size-4 shrink-0" />
        <span className="truncate">{label}</span>
        <span className="ml-auto text-[10px] uppercase tracking-wide">Próximamente</span>
      </span>
    )
  }
  return (
    <Link
      href={href}
      onClick={onClick}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        BASE,
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        isActive
          ? "bg-primary text-primary-foreground"
          : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
      )}
    >
      <Icon className="size-4 shrink-0" />
      {label}
    </Link>
  )
}
