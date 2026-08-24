import { useRol } from "@/hooks/useRol"
import { puede, type Accion, type Seccion } from "@/services/permisos"

interface CanProps {
  seccion: Seccion
  accion?: Accion
  children: React.ReactNode
}

/**
 * Renderiza children solo si el rol actual puede ejecutar (seccion, accion).
 * UX: oculta lo que el rol no puede usar. NO es seguridad (el backend da 403).
 * Por defecto gatea escritura, el caso de uso de 16.6.
 *
 * 🔴 El rol sale de `useRol()` y NO de `getRol()` directo: llamarlo en el render leía
 * localStorage, que el servidor no tiene, y el HTML server-rendered quedaba sin los children
 * mientras el cliente los agregaba — mismatch de hidratación. El porqué está en hooks/useRol.ts.
 */
export function Can({ seccion, accion = "write", children }: CanProps) {
  return puede(useRol(), seccion, accion) ? <>{children}</> : null
}
