import { validarEmail } from "@/components/features/shared/validacionEmail"
import { ROL_LABEL, type UserRol } from "@/types/auth"

/**
 * La forma y la validación del alta de usuario: función pura, sin React.
 *
 * 🔴 POR QUÉ SALIÓ DEL MODAL. `CrearUsuarioModal.tsx` quedó en **152/150 líneas** al migrar su
 * email al validador compartido, y el límite de un componente no se paga borrando el comentario
 * que explica por qué el mensaje dice lo que dice. El corte es el mismo que el repo ya usa en
 * `AreaModal` / `ClienteModal` y el que esta misma tanda estrenó en
 * `candidatos/_contratarForm.ts`: **los campos y la validación a un `_*.ts` puro, el modal se
 * queda con el render**.
 *
 * Y hay una razón que no es de líneas: `vitest` corre con `environment: "node"`, así que un
 * modal sólo se puede probar por su markup estático. Una `validar(form) → errores por campo` es
 * lo único de un formulario que esta suite puede ejercitar de verdad.
 */

export type FormData = {
  nombre: string; apellido: string; email: string; username: string; rol: string; empleadoId: string
}

export type FormErrors = Partial<Record<Exclude<keyof FormData, "empleadoId" | "rol">, string>>

export const EMPTY: FormData = {
  nombre: "", apellido: "", email: "", username: "", rol: "mandos_medios", empleadoId: "",
}

export const ROL_OPTIONS = (Object.keys(ROL_LABEL) as UserRol[])
  .map((r) => ({ value: r, label: ROL_LABEL[r] }))

/** Los errores por campo, o `{}` si el formulario sirve. */
export function validate(f: FormData): FormErrors {
  const e: FormErrors = {}
  if (!f.nombre.trim()) e.nombre = "El nombre es requerido"
  if (!f.apellido.trim()) e.apellido = "El apellido es requerido"
  // Antes decía "El email es requerido" / "Formato de email inválido". Los dos son los ejemplos
  // textuales que §3 usa para explicar un mensaje que NO ayuda: el asterisco ya dice que es
  // obligatorio, y "inválido" no dice si falta el arroba, si sobra un espacio o si el dominio
  // está incompleto. Ahora usa el validador compartido, con los mensajes de /empleados.
  const errorEmail = validarEmail(f.email, { vacio: "Escribí el email con el que va a entrar al sistema" })
  if (errorEmail) e.email = errorEmail
  if (f.username.trim().length < 3) e.username = "Mínimo 3 caracteres"
  return e
}
