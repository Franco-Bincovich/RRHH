import { usePathname } from "next/navigation"

import { getRol, puede, seccionDeRuta, type Seccion } from "@/services/permisos"

/**
 * UX: ¿el rol actual puede escribir en esta sección? Solo para ocultar entry points
 * de escritura (no es control de seguridad — el backend responde 403).
 *
 * Sin argumento deriva la sección del pathname; las rutas no gateadas devuelven true
 * (no se ocultan acciones). Con `seccion` explícita la usa tal cual (para componentes
 * que no conocen su ruta, p. ej. el tab de áreas dentro de /empresas/[id]).
 */
export function useCanWrite(seccion?: Seccion): boolean {
  const pathname = usePathname()
  const sec = seccion ?? seccionDeRuta(pathname)
  return sec ? puede(getRol(), sec, "write") : true
}

/**
 * UX: ¿el rol actual puede LEER esta sección? Para ocultar bloques cuyo contenido pertenece a
 * otra sección que la de la página — p. ej. el historial salarial dentro de la ficha del
 * empleado, que es un dato de costos.
 *
 * Igual que useCanWrite, NO es control de seguridad: el backend gatea igual y responde 403.
 * Lo que evita es una sección que aparece y falla, que es peor que una que no aparece.
 * La sección va siempre explícita: si un bloque necesita este hook es justamente porque su
 * contenido no es el de la ruta en la que está.
 */
export function useCanRead(seccion: Seccion): boolean {
  return puede(getRol(), seccion, "read")
}
