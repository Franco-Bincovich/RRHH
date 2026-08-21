export interface FormLogin {
  username: string
  password: string
}

export type ErroresLogin = Partial<Record<keyof FormLogin, string>>

/**
 * La validación local del login, separada del componente para poder probarla sin DOM (el proyecto
 * corre vitest sin jsdom).
 *
 * 🔴 LOS MENSAJES DICEN QUÉ CORREGIR Y NO "campo inválido" (`docs/SISTEMA-DE-DISENO.md` §3). Con
 * dos campos parece un detalle; no lo es para el caso que este formulario tiene que resolver de
 * verdad: alguien que entra por primera vez con una contraseña temporal que le pasaron por otro
 * lado y no sabe si el problema es lo que escribió o lo que le dieron.
 *
 * ⚠️ NO valida el LARGO de la contraseña ni el formato del usuario, a propósito: el mínimo de 8
 * caracteres es una regla del ALTA, no del ingreso. Aplicarla acá rechazaría a alguien con una
 * contraseña vieja más corta antes de preguntarle al backend, y le diría que su contraseña está
 * mal formada cuando en realidad funcionaría.
 */
export function validarLogin(form: FormLogin): ErroresLogin {
  const errores: ErroresLogin = {}
  if (!form.username.trim()) errores.username = "Ingresá tu usuario"
  if (!form.password) errores.password = "Ingresá tu contraseña"
  return errores
}
