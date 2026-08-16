import { ApiError } from "@/services/api"

/**
 * Mensaje a mostrar cuando falla un alta o una edición de evento.
 *
 * 🔴 EL MENSAJE DEL BACKEND SE CONSERVA cuando es un error de la API. El caso concreto que este
 * formulario produce es el de crear un evento con el selector en "Todas las empresas": el
 * backend responde `EMPRESA_ID_REQUIRED` (400) con un texto escrito para RRHH —"Elegí una
 * empresa en el selector de arriba a la izquierda"— que dice EXACTAMENTE el paso siguiente.
 * Reemplazarlo por "No se pudo guardar. Intentá de nuevo." sería además el consejo equivocado:
 * reintentar sin tocar el selector nunca funciona.
 *
 * El genérico queda solo para lo que NO es un error de la API (red caída, timeout), donde
 * reintentar sí es lo razonable. Mismo criterio y mismo motivo de vivir suelta que
 * `erroresCliente.ts`: se testea sin DOM, y el proyecto corre vitest SIN jsdom.
 */
export function mensajeDeError(e: unknown): string {
  return e instanceof ApiError ? e.message : "No se pudo guardar. Intentá de nuevo."
}
