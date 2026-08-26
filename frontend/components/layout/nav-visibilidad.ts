import {
  ADMIN_GROUP, ITEMS_SUPERIORES, NAV_GROUPS, RUTAS_OCULTAS, TODOS_LOS_GRUPOS,
  type NavGroupDef, type NavLink,
} from "@/components/layout/nav-config"
import { puede } from "@/services/permisos"
import type { UserRol } from "@/types/auth"

/** ¿La ruta activa cae dentro de este ítem? Los `proximamente` no tienen href: nunca son activos. */
export function esActivo(href: string | undefined, pathname: string): boolean {
  if (!href) return false
  return pathname === href || pathname.startsWith(`${href}/`)
}

/** Label del grupo que contiene la ruta activa, o null (para abrirlo por defecto). */
export function grupoDeRuta(pathname: string): string | null {
  const g = TODOS_LOS_GRUPOS.find((grp) => grp.items.some((i) => esActivo(i.href, pathname)))
  return g?.label ?? null
}

/** ¿El rol puede ver este item? Gating de sección (existente) + gating opcional por rol (soloRol).
 *  Sin soloRol → solo cuenta la sección (retrocompat). rol=null (pre-mount) → un item con soloRol
 *  no se muestra (null no está en ninguna lista), evitando flash hasta conocer el rol. */
export function itemVisible(item: NavLink, rol: UserRol | null): boolean {
  // Las secciones ocultas se filtran ACÁ y no sacándolas de NAV_GROUPS: éste es el único punto
  // por el que ya pasaba la pregunta, así que las tres superficies (los 6 grupos, Administración
  // y los ítems superiores) quedan cubiertas sin repetir el filtro. El porqué de dejar el ítem
  // declarado en la estructura está en `RUTAS_OCULTAS`. ⚠️ Va ANTES del permiso a propósito: si
  // la sección no se muestra, el rol es una pregunta que ya no hace falta contestar.
  if (item.href && RUTAS_OCULTAS.includes(item.href)) return false
  const seccionOk = item.seccion === null || (rol !== null && puede(rol, item.seccion, item.accion ?? "read"))
  const rolOk = !item.soloRol || (rol !== null && item.soloRol.includes(rol))
  return seccionOk && rolOk
}

/** Grupos con sus items filtrados por permiso; se descartan los que quedan vacíos. */
function filtrar(grupos: ReadonlyArray<NavGroupDef>, rol: UserRol | null): NavGroupDef[] {
  return grupos
    .map((g) => ({ label: g.label, icon: g.icon, items: g.items.filter((i) => itemVisible(i, rol)) }))
    .filter((g) => g.items.length > 0)
}

/** Los 6 grupos del sistema de diseño, ya filtrados. */
export function gruposVisibles(rol: UserRol | null): NavGroupDef[] {
  return filtrar(NAV_GROUPS, rol)
}

/** Administración, al final y separada de los 6. null si el rol no ve ninguno de sus items. */
export function adminVisible(rol: UserRol | null): NavGroupDef | null {
  return filtrar([ADMIN_GROUP], rol)[0] ?? null
}

/** Los items de arriba (Dashboard · Reportes · Auditoría) que el rol puede ver. */
export function superioresVisibles(rol: UserRol | null): NavLink[] {
  return ITEMS_SUPERIORES.filter((i) => itemVisible(i, rol))
}
