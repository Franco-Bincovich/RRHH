/**
 * Cuánto hace que este navegador no le habla al backend.
 *
 * 🔑 Mide REQUESTS, no interacción, porque es el mismo reloj que mira el backend: allá la
 * sesión vence a las 8 h sin un solo request (`utils/_sesion_inactividad.py`). Un contador
 * basado en mousemove o teclado avisaría distinto de lo que el servidor va a hacer — le diría
 * al usuario que le quedan horas mientras el backend lo está por echar, que es peor que no
 * avisar nada.
 *
 * Esto es UX y NADA MÁS: el corte lo hace el backend en cada request. Si alguien borra este
 * archivo entero, la sesión vence igual; lo único que se pierde es el aviso.
 *
 * Módulo hoja, sin imports del proyecto: lo consume `authRefresh` (que está debajo de todo en
 * la cadena de módulos) y no puede arrastrar dependencias.
 */

/** Espejo de INACTIVIDAD_MAXIMA del backend. Si allá cambia, acá también. */
export const INACTIVIDAD_MAXIMA_MS = 8 * 60 * 60 * 1000

/** Cuánto antes del corte se avisa: 15 minutos → el aviso aparece a las 7 h 45 min. */
export const AVISO_ANTES_MS = 15 * 60 * 1000

// Arranca "ahora": cargar la página ES actividad — la carga misma dispara requests.
let ultimaActividad = Date.now()

/** La llama el wrapper de fetch ante CUALQUIER respuesta: el backend ya vio ese request. */
export function marcarActividad(): void {
  ultimaActividad = Date.now()
}

export function msDesdeActividad(ahora: number = Date.now()): number {
  return ahora - ultimaActividad
}

/**
 * ¿Hay que mostrar el aviso?
 *
 * Deja de avisar una vez pasado el máximo: a esa altura el próximo request va a devolver 401 y
 * el interceptor manda al login solo. Un banner que diga "te quedan -3 minutos" no ayuda a
 * nadie.
 */
export function debeAvisar(transcurrido: number): boolean {
  return transcurrido >= INACTIVIDAD_MAXIMA_MS - AVISO_ANTES_MS && transcurrido < INACTIVIDAD_MAXIMA_MS
}

/** Minutos que faltan para el corte, redondeados hacia arriba y nunca por debajo de 1. */
export function minutosRestantes(transcurrido: number): number {
  return Math.max(1, Math.ceil((INACTIVIDAD_MAXIMA_MS - transcurrido) / 60000))
}
