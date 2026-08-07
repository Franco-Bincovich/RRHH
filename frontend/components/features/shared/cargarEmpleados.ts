import { fetchEmpleados, type EmpleadosFiltros } from "@/services/empleados"
import type { Empleado } from "@/types/empleado"

/**
 * Los setters de un selector de empleados. Se inyectan en vez de vivir dentro del hook para que
 * la carga se pueda testear sin renderizar: vitest corre SIN jsdom, así que un `useEffect` no se
 * ejecuta y un test de componente no puede ver ninguno de los tres desenlaces. Molde:
 * `components/features/proyectos/cargarProyectos.ts`.
 */
export interface EstadoEmpleados {
  setEmpleados: (e: Empleado[]) => void
  setCargando: (v: boolean) => void
  /** `true` = la consulta FALLÓ. Es lo que distingue el error de una lista vacía de verdad. */
  setError: (v: boolean) => void
}

/**
 * Carga empleados para un selector y deja el estado en UNO de tres desenlaces: cargando, error,
 * o lista (que puede estar vacía legítimamente). Nunca lanza.
 *
 * 🔴 EL `setError(true)` ES LA RAZÓN DE SER DE ESTE MÓDULO. Antes cada hook hacía
 * `.catch(() => setEmpleados([]))` y descartaba el error, así que un fallo de red, un 401, un 403
 * y un 422 llegaban a la pantalla con la misma cara: "no hay empleados". La UI afirmaba un hecho
 * sobre los datos cuando lo que hubo fue un error, y eso manda al usuario a buscar el problema
 * donde no está.
 *
 * No es hipotético: así se hizo invisible un `page_size=200` contra un endpoint con `le=100`. El
 * backend respondía 422 en el 100% de los requests y dos modales mostraron "no hay empleados"
 * durante meses, con 31 activos en la base y la suite en verde.
 *
 * 🔴 EL `finally` APAGA EL LOADING SIEMPRE, también en el camino de error. Apagarlo dentro del
 * `try` deja la pantalla cargando encima del mensaje que el `catch` acaba de escribir — el
 * usuario nunca llega a leerlo (es la regresión que se llevó puesta la pantalla de proyectos).
 *
 * `?? []` cubre el 200 sin `items`: sin eso la lista revienta al leer `.length` y el síntoma
 * vuelve a ser una pantalla en blanco que no dice qué pasó.
 */
export async function cargarEmpleados(
  filtros: EmpleadosFiltros & { page: number; pageSize: number },
  estado: EstadoEmpleados,
): Promise<void> {
  estado.setCargando(true)
  estado.setError(false)
  try {
    const data = await fetchEmpleados(filtros)
    estado.setEmpleados(data.items ?? [])
  } catch {
    // La lista se vacía ADEMÁS de marcar el error: si quedara la anterior, la pantalla mostraría
    // datos viejos al lado de un cartel que dice que no se pudieron cargar.
    estado.setEmpleados([])
    estado.setError(true)
  } finally {
    estado.setCargando(false)
  }
}
