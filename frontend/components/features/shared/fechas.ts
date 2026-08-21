/**
 * Las dos cuentas de fecha que las pantallas del ciclo de vida (`/proximos-ingresos`, `/bajas`)
 * necesitan y que el backend NO manda: cómo se escribe una fecha y cuántos días faltan para una.
 * (La tercera —la antigüedad— ya existía; ver la nota al pie.)
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 NINGUNA USA `new Date(iso)` A SECAS, Y ES LA DECISIÓN DE TODO EL ARCHIVO.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * `new Date("2026-10-01")` parsea como MEDIANOCHE UTC. En Argentina (UTC-3) eso se renderiza
 * como el 30/09: la pantalla mostraría todas las fechas un día antes, y el contador de "faltan N
 * días" estaría corrido uno. El repo ya paga este bug con un `T00:00:00` pegado al string en
 * `EventosTabla` y en `HorasTab`, cada uno con su comentario diciendo lo mismo, porque —dice ese
 * comentario— "el repo todavía no tiene un formateador compartido". Ahora lo tiene.
 *
 * Acá los dos lados de cada resta se llevan al MISMO plano (mediodía UTC no hace falta: se
 * comparan enteros de `Date.UTC`, que no tienen hora ni huso), y "hoy" entra por parámetro para
 * que los tests no dependan del día en que corran.
 *
 * ⚠️ NO se agregó `T00:00:00` + `toLocaleDateString` como en las dos tablas viejas: eso resuelve
 * el formateo pero NO la resta, que es donde el huso vuelve a entrar (un `Date` local restado
 * contra otro local cruza cambios de horario de verano y da 0,96 días). Las dos funciones
 * trabajan sobre el mismo entero UTC.
 */

/** El `YYYY-MM-DD` de un ISO (con o sin hora) llevado a entero UTC. `null` si no se puede leer. */
function aUTC(iso: string | null | undefined): number | null {
  if (!iso) return null
  const [anio, mes, dia] = iso.slice(0, 10).split("-").map(Number)
  if (!anio || !mes || !dia) return null
  return Date.UTC(anio, mes - 1, dia)
}

/** El día de HOY según el reloj LOCAL del usuario, llevado al mismo plano UTC que `aUTC`. */
function hoyUTC(hoy: Date): number {
  return Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate())
}

const UN_DIA = 86_400_000

/** "2026-03-25" → "25/03/2026". Vacío, nulo o ilegible → "—". */
export function formatFecha(iso: string | null | undefined): string {
  if (!iso) return "—"
  const [anio, mes, dia] = iso.slice(0, 10).split("-")
  return dia && mes && anio ? `${dia}/${mes}/${anio}` : iso
}

/**
 * Cuántos días faltan para `iso`. Negativo = ya pasó, `0` = hoy.
 *
 * `hoy` entra por parámetro con default: sin eso, un test que afirme "faltan 5 días" solo pasa
 * el día que se escribió. Los llamadores de producción no lo pasan.
 */
export function diasHasta(iso: string, hoy: Date = new Date()): number | null {
  const objetivo = aUTC(iso)
  return objetivo === null ? null : Math.round((objetivo - hoyUTC(hoy)) / UN_DIA)
}

/**
 * ⚠️ ACÁ NO VIVE LA ANTIGÜEDAD, A PROPÓSITO. `antiguedad(desde, hasta)` YA EXISTE, en
 * `components/features/empleados/ficha/_datosClave.ts`, donde la usa la barra de identidad: su
 * segundo parámetro es la fecha CONTRA la que se mide, con `hoyISO()` de default, así que
 * "antigüedad al egreso" es esa misma función pasándole la fecha de egreso. Escribir una
 * segunda acá habría dado dos definiciones de la antigüedad de una persona —el número con el
 * que RRHH calcula indemnizaciones— divergiendo en el primer cambio. `_bajas.ts` la importa de
 * allá y le pone la única regla que sí es de esta pantalla: qué hacer sin fecha de egreso.
 */
