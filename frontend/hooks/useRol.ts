import { useSyncExternalStore } from "react"

import { getRol } from "@/services/permisos"
import type { UserRol } from "@/types/auth"

/**
 * 🔴 DE DÓNDE SALE EL ROL EN UN RENDER. Módulo propio, y no una línea dentro de useCanWrite,
 * por dos motivos: es la ÚNICA pieza que toca un store del navegador durante el render, y es la
 * costura que los tests de pantalla falsean para poder probar el gate por rol sin falsear
 * `puede()` (que es lo que haría vacuo el test).
 *
 * EL PROBLEMA: `getRol()` lee localStorage, que en el servidor no existe. Llamarlo en el cuerpo
 * de un componente hace que el HTML server-rendered salga SIN los botones de escritura y que el
 * primer render del cliente los agregue — mismatch de hidratación (React #418) en las 20
 * pantallas donde el rol puede escribir. Y no es solo ruido en consola: ante un mismatch React
 * DESCARTA el árbol server-rendered y lo regenera en el cliente, así que se paga el server
 * render y no se aprovecha.
 *
 * LA SALIDA: `useSyncExternalStore` es la API que React expone exactamente para un store
 * externo que el servidor no puede leer. Durante la hidratación usa el snapshot DEL SERVIDOR
 * —null, o sea fail-closed, o sea el mismo HTML que se emitió— y recién después lee el del
 * cliente y re-renderiza. React sabe de esa divergencia: no la trata como error ni tira el árbol.
 *
 * ⚠️ LOS BOTONES SIGUEN APARECIENDO AL HIDRATAR, Y ESO NO LO AGREGA ESTE CAMBIO: ya pasaba, y
 * es inevitable mientras el rol viva solo en el cliente. La única salida sin ese salto es que
 * el servidor conozca el rol —moverlo de localStorage a una cookie que el layout pueda leer—,
 * que es una tanda propia sobre auth con su propia trampa (cookie y localStorage drifteando),
 * no un arreglo de hidratación. Anotado en docs/DEUDA-TECNICA.md.
 *
 * ⚠️ NO agregar acá un "ya hidraté" con useState+useEffect: eso re-renderiza DESPUÉS del paint
 * (garantizado por spec), o sea que agrega el parpadeo que este camino no tiene.
 */
function suscribir(alCambiar: () => void): () => void {
  if (typeof window === "undefined") return () => {}
  // Cross-tab: si otra pestaña cierra sesión, ésta deja de ofrecer acciones de escritura.
  window.addEventListener("storage", alCambiar)
  return () => window.removeEventListener("storage", alCambiar)
}

/**
 * El rol del usuario para un render. En el servidor y durante la hidratación es `null`
 * (fail-closed); en el cliente, el de la sesión guardada.
 */
export function useRol(): UserRol | null {
  return useSyncExternalStore(suscribir, getRol, () => null)
}
