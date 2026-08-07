import { fetchHistorialMails } from "@/services/mails"
import type { MailEnviado, MailsFiltros } from "@/types/plantillas"

/**
 * Los setters del historial. Se inyectan en vez de vivir dentro del hook para que la carga se
 * pueda testear sin renderizar: vitest corre SIN jsdom, así que un `useEffect` no se ejecuta y
 * un test de componente no puede ver ninguno de los tres desenlaces. Molde:
 * `components/features/shared/cargarEmpleados.ts` y `proyectos/cargarProyectos.ts`.
 */
export interface EstadoHistorial {
  setItems: (i: MailEnviado[]) => void
  setLimite: (n: number) => void
  setCargando: (v: boolean) => void
  /** `true` = la consulta FALLÓ. Es lo que distingue el error de un historial vacío de verdad. */
  setError: (v: boolean) => void
}

/**
 * Carga el historial y deja el estado en UNO de tres desenlaces: cargando, error, o lista (que
 * puede estar vacía legítimamente — nadie mandó un mail todavía). Nunca lanza.
 *
 * 🔴 EL `setError(true)` NO ES DECORACIÓN. Un `.catch` que pinte lista vacía dice "todavía no se
 * envió ningún mail" cuando lo que hubo fue un fallo de red o un 403, y eso manda al usuario a
 * buscar el problema donde no está. Ya pasó en este repo: dos modales mostraron "no hay
 * empleados" con la base llena porque el `catch` tragaba un 422. Los tres estados existen para
 * que ese modo de falla no pueda volver por esta puerta.
 */
export async function cargarHistorialMails(
  filtros: MailsFiltros,
  estado: EstadoHistorial,
): Promise<void> {
  estado.setCargando(true)
  estado.setError(false)
  try {
    const data = await fetchHistorialMails(filtros)
    // `?? []` cubre un 200 sin `items`: sin eso la tabla revienta al mapear y el síntoma vuelve
    // a ser una pantalla en blanco que no dice qué pasó.
    estado.setItems(data.items ?? [])
    estado.setLimite(data.limite ?? 0)
  } catch {
    estado.setItems([])
    estado.setError(true)
  } finally {
    estado.setCargando(false)
  }
}
