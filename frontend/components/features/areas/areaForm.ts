/**
 * Los tipos y la validación del formulario de área, como funciones puras.
 *
 * Extraído de `AreaModal.tsx`, que estaba en 207/150. El corte es el molde de
 * `vacacionesForm.ts` y `ausenciasForm.ts`: la decisión de qué es válido vive afuera del
 * componente, así que se puede testear sin DOM — el proyecto corre vitest SIN jsdom, y un
 * modal montado por portal de Radix devuelve markup vacío.
 */

export type FormData = {
  /** UUID de la empresa DUEÑA. "" = el sidebar está en "Todas las empresas" y falta elegirla. */
  empresa_id: string
  nombre: string
  descripcion: string
  responsable_id: string
}

export type FormErrors = Partial<Record<keyof FormData, string>>

export const EMPTY: FormData = { empresa_id: "", nombre: "", descripcion: "", responsable_id: "" }

export const SELECT_CLASS =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

/**
 * Errores del formulario. Objeto vacío = se puede mandar.
 *
 * 🔴 La empresa se exige SOLO en el alta: `AreaUpdate` no la lleva (un área no se muda de
 * sociedad), así que en la edición no hay nada que validar y exigirla rompería editar.
 *
 * A diferencia de clientes, **un área SÍ pertenece a una empresa**: este select y esta
 * validación se quedan para siempre, no son transitorios.
 */
export function validate(form: FormData, isEdit: boolean): FormErrors {
  const errors: FormErrors = {}
  if (!isEdit && !form.empresa_id) errors.empresa_id = "Requerido"
  if (!form.nombre.trim()) errors.nombre = "El nombre es requerido"
  else if (form.nombre.trim().length > 100) errors.nombre = "Máximo 100 caracteres"
  return errors
}
