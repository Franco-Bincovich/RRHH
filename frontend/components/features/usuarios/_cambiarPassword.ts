export type FormData = { actual: string; nueva: string; confirmar: string }
export type FormErrors = Partial<Record<keyof FormData, string>>

export const EMPTY: FormData = { actual: "", nueva: "", confirmar: "" }

/**
 * La validación del cambio de contraseña, separada del componente para poder probarla sin DOM (el
 * proyecto corre vitest sin jsdom, así que lo único que se puede afirmar de verdad son las
 * funciones puras).
 *
 * 🔴 LOS MENSAJES DICEN QUÉ CORREGIR (`docs/SISTEMA-DE-DISENO.md` §3), no "campo inválido".
 * "Mínimo 8 caracteres" ya se leía bien y se dejó tal cual; los otros dos decían el problema en
 * vez de la salida —"La nueva contraseña debe ser distinta de la actual", "Las contraseñas no
 * coinciden"— y ahora nombran la acción.
 *
 * ⚠️ EL ORDEN DE LOS `if` DE `nueva` IMPORTA Y NO ES INTERCAMBIABLE: si la contraseña es corta se
 * dice eso y no se la compara con la actual. Decirle a alguien "elegí una distinta de la actual"
 * sobre una cadena de tres letras lo manda a resolver el problema equivocado.
 */
export function validarCambio(f: FormData): FormErrors {
  const e: FormErrors = {}
  if (!f.actual) e.actual = "Ingresá tu contraseña actual"
  if (f.nueva.length < 8) e.nueva = "Mínimo 8 caracteres"
  else if (f.nueva === f.actual) e.nueva = "Elegí una distinta de la actual"
  if (f.confirmar !== f.nueva) e.confirmar = "Repetí la nueva contraseña: no coinciden"
  return e
}
