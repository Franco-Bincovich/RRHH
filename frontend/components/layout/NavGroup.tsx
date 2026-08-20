"use client"

import type { ElementType } from "react"
import { ChevronDown } from "lucide-react"

import { cn } from "@/lib/utils"
import { NavItem } from "@/components/layout/NavItem"
import { esActivo } from "@/components/layout/nav-visibilidad"
import type { NavLink } from "@/components/layout/nav-config"

interface NavGroupProps {
  label: string
  icon: ElementType
  items: NavLink[] // ya filtrados por permiso (el grupo se renderiza solo si hay ≥1)
  open: boolean
  onToggle: () => void
  pathname: string
  onNavigate: () => void
}

/** Grupo colapsable del sidebar: header-botón accesible (aria-expanded + chevron) + items.
 *
 *  El contador es la cantidad de items VISIBLES del grupo y solo se muestra cerrado. No es un
 *  número fijo: sale del filtrado por permiso, así que un mando medio y un admin ven distinto,
 *  y su única función es decir cuánto hay detrás de un grupo cerrado. El sistema de diseño no
 *  pide otra cosa acá: las alertas y pendientes viven en el dashboard (§6), no en el sidebar. */
export function NavGroup({ label, icon: Icon, items, open, onToggle, pathname, onNavigate }: NavGroupProps) {
  return (
    <li>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className={cn(
          "flex min-h-11 w-full items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors",
          "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        )}
      >
        <Icon className="size-4 shrink-0" />
        <span className="flex-1 text-left">{label}</span>
        {!open && (
          <span className="rounded-full bg-sidebar-accent px-1.5 text-[11px] tabular-nums text-sidebar-accent-foreground">
            {items.length}
          </span>
        )}
        <ChevronDown className={cn("size-4 shrink-0 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <ul className="mt-1 space-y-1 pl-3" role="list">
          {items.map((item) => (
            <li key={item.href ?? item.label}>
              <NavItem
                href={item.href}
                label={item.label}
                icon={item.icon}
                isActive={esActivo(item.href, pathname)}
                onClick={onNavigate}
                proximamente={item.proximamente}
              />
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}
