/**
 * Direcciones escritas a mano: parseo y validación de formato. Módulo puro, sin React.
 *
 * 🔴 ESTO NO ES LA FRONTERA. La misma validación corre en el backend
 * (`services/_envio_libre.py`), que es donde de verdad se decide: el endpoint se puede llamar
 * sin pasar por esta pantalla. Lo de acá existe para no frustrar —deshabilitar antes de apretar,
 * en vez de un error después— y por eso puede ser más permisivo sin abrir ningún agujero.
 *
 * El patrón es el MISMO que el del backend, a propósito conservador: ataja el typo (`ana@`,
 * `ana k.com`, `ana@k`), no certifica direcciones exóticas. Lo que pase y no exista igual va a
 * fallar en el envío y quedar registrado como `fallido` en el historial.
 */

const EMAIL = /^[^@\s,;]+@[^@\s,;]+\.[A-Za-z]{2,}$/

/** El motivo que se muestra cuando el modo libre está deshabilitado. Lo importa el test. */
export const MOTIVO_VARIABLES =
  "Esta plantilla usa datos del colaborador, así que solo se puede enviar a colaboradores del sistema."

export function emailValido(direccion: string): boolean {
  return EMAIL.test((direccion ?? "").trim())
}

/**
 * Texto del campo → lista de direcciones. Acepta coma, punto y coma y salto de línea como
 * separadores: es lo que sale de copiar y pegar desde un Excel, un mail o una lista escrita a
 * mano, y exigir un separador único convierte un pegado en un error que el usuario no entiende.
 *
 * Dedup case-insensitive conservando la primera forma escrita: pegar dos veces la misma dirección
 * es normal, mandarle dos mails idénticos a alguien de afuera no.
 */
export function parsearDirecciones(texto: string): string[] {
  const vistas = new Map<string, string>()
  for (const parte of (texto ?? "").split(/[\s,;]+/)) {
    const limpia = parte.trim()
    if (limpia && !vistas.has(limpia.toLowerCase())) vistas.set(limpia.toLowerCase(), limpia)
  }
  return [...vistas.values()]
}

/** Las que NO tienen forma de dirección. `[]` = se puede enviar. */
export function direccionesInvalidas(direcciones: string[]): string[] {
  return direcciones.filter((d) => !emailValido(d))
}
