import { ApiError } from "@/services/api"

/**
 * Mensaje a mostrar cuando falla un alta o una edición de cliente.
 *
 * 🔴 EL MENSAJE DEL BACKEND SE CONSERVA. El único error de negocio que este formulario puede
 * producir es `CLIENTE_DUPLICADO` (409), y su texto —"Ya existe un cliente con ese nombre"— es
 * exactamente lo que el usuario necesita para resolverlo. Reemplazarlo por un
 * genérico deja a alguien de RRHH apretando "Crear" sin entender por qué no pasa nada, y
 * "Intentá de nuevo" sería además el consejo equivocado: reintentar el mismo nombre nunca
 * funciona. El genérico queda solo para lo que NO es un error de la API (red caída, timeout),
 * donde reintentar sí es lo razonable.
 *
 * Mismo criterio, y mismo motivo de estar en un módulo aparte, que `mensajeDeError` de
 * `ExportMenu`: se exporta suelta para poder testear la decisión sin un DOM — el proyecto corre
 * vitest SIN jsdom.
 */
export function mensajeDeError(e: unknown): string {
  return e instanceof ApiError ? e.message : "No se pudo guardar. Intentá de nuevo."
}
