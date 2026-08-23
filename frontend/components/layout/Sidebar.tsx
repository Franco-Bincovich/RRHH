"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Menu, X, Building2 } from "lucide-react"

import { cn } from "@/lib/utils"
import { Separator } from "@/components/ui/separator"
import { UserMenu } from "@/components/layout/UserMenu"
import { EmpresaSelector } from "@/components/layout/EmpresaSelector"
import { ThemeToggle } from "@/components/layout/ThemeToggle"
import { NavItem } from "@/components/layout/NavItem"
import { NavGroup } from "@/components/layout/NavGroup"
import type { NavGroupDef } from "@/components/layout/nav-config"
import {
  adminVisible, esActivo, grupoDeRuta, gruposVisibles, superioresVisibles,
} from "@/components/layout/nav-visibilidad"
import { getRol } from "@/services/permisos"
import type { UserRol } from "@/types/auth"

export function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [rol, setRol] = useState<UserRol | null>(null)
  const pathname = usePathname()
  /**
   * Acordeón: un solo grupo abierto. Arranca en el que contiene la ruta activa.
   *
   * 🔴 EXCEPCIÓN DECLARADA a "todo desplegable nace plegado" — la razón completa está en
   * `components/ui/barridoAcordeones.test.ts`, que rojea si alguien la cambia sin sacarla de la
   * lista. En una línea: esto no es "abierto por defecto", es abierto PORQUE EL USUARIO ESTÁ
   * ADENTRO, y plegarlo esconde la pantalla en la que está sin recuperar nada (`openGroup` es un
   * solo valor, así que nunca hay más de un grupo desplegado).
   */
  const [openGroup, setOpenGroup] = useState<string | null>(() => grupoDeRuta(pathname))

  // El rol se lee tras montar (localStorage) para no romper la hidratación SSR.
  useEffect(() => {
    setRol(getRol())
  }, [])

  // Los 6 grupos + Administración aparte, ya filtrados por permiso (los vacíos se descartan).
  const visibleGroups = gruposVisibles(rol)
  const admin = adminVisible(rol)
  const superiores = superioresVisibles(rol)

  const closeMobile = () => setMobileOpen(false)
  const toggleGroup = (label: string) => setOpenGroup((cur) => (cur === label ? null : label))

  const renderGrupo = (g: NavGroupDef) => (
    <NavGroup
      key={g.label}
      label={g.label}
      icon={g.icon}
      items={g.items}
      open={openGroup === g.label}
      onToggle={() => toggleGroup(g.label)}
      pathname={pathname}
      onNavigate={closeMobile}
    />
  )

  return (
    <>
      {/* Hamburger — solo mobile */}
      <button
        className="fixed left-4 top-4 z-50 flex min-h-11 min-w-11 items-center justify-center rounded-lg bg-sidebar text-sidebar-foreground shadow-sm ring-1 ring-sidebar-border transition-colors hover:bg-sidebar-accent lg:hidden"
        onClick={() => setMobileOpen(true)}
        aria-label="Abrir menú"
      >
        <Menu className="size-5" />
      </button>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" aria-hidden="true" onClick={closeMobile} />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-sidebar ring-1 ring-sidebar-border transition-transform duration-200",
          "lg:relative lg:z-auto lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Header: logo + tema + cerrar */}
        <div className="flex h-14 items-center justify-between px-4">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 text-sm font-semibold text-sidebar-foreground"
            onClick={closeMobile}
          >
            <Building2 className="size-5 text-primary" />
            <span>HR Karstec</span>
          </Link>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <button
              className="flex min-h-11 min-w-11 items-center justify-center rounded-lg text-sidebar-foreground transition-colors hover:bg-sidebar-accent lg:hidden"
              onClick={closeMobile}
              aria-label="Cerrar menú"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>

        <Separator />

        <div className="px-0 pt-2">
          <EmpresaSelector />
        </div>

        <Separator />

        {/* Navegación: Dashboard · Reportes · Auditoría fijos arriba, fuera de los grupos
            (sistema de diseño §4); después los 6 grupos; Administración al final, separada. */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <ul className="space-y-1" role="list">
            {superiores.map((item) => (
              <li key={item.href}>
                <NavItem
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  isActive={esActivo(item.href, pathname)}
                  onClick={closeMobile}
                />
              </li>
            ))}
            <li aria-hidden="true" className="my-2 border-t border-sidebar-border" />
            {visibleGroups.map(renderGrupo)}
            {admin && (
              <>
                <li aria-hidden="true" className="my-2 border-t border-sidebar-border" />
                {renderGrupo(admin)}
              </>
            )}
          </ul>
        </nav>

        <Separator />

        <div className="p-3">
          <UserMenu />
        </div>
      </aside>
    </>
  )
}
