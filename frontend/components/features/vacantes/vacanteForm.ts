import type { VacanteCreate } from "@/types/vacantes"

/**
 * Shape del form de alta de vacante + constantes, validación y payload. Puro: sin JSX, sin
 * React, sin red.
 *
 * Molde: `components/features/vacaciones/vacacionesForm.ts`, que resuelve exactamente esto para
 * el alta de vacaciones y ya fija el reparto — el tipo del form, su `EMPTY`, la clase de los
 * `<select>`, la validación y los constructores de payload viven juntos y aparte del modal.
 *
 * ⚠️ LOS CINCO SÍMBOLOS ERAN PRIVADOS DE VacanteModal.tsx (ninguno estaba exportado), así que
 * llevan prefijo al salir. No es un renombre de API pública: es que `FormData` exportado pisaría
 * el global del DOM para quien lo importe, y `validate` a secas no dice de qué. Es el mismo
 * criterio con el que `vacacionesForm` los llama `VacacionFormData` y `validateVacacion`.
 *
 * 📌 QUÉ VA A CRECER ACÁ. El selector de perfil de puesto suma `perfil_puesto_id` a este tipo y
 * a `EMPTY_VACANTE`, y la copia de los campos descriptivos se escribe como una función pura
 * `desdePerfil(perfil): Partial<VacanteFormData>` — testeable sin montar el modal, que hoy no
 * tiene un solo test (ver el encabezado de VacanteModal.tsx).
 */
export type VacanteFormData = {
  empresa_id: string
  titulo: string
  area_id: string
  tipo_contrato: string
}

export type VacanteFormErrors = Partial<Record<keyof VacanteFormData, string>>

export const EMPTY_VACANTE: VacanteFormData = {
  empresa_id: "",
  titulo: "",
  area_id: "",
  tipo_contrato: "efectivo",
}

/**
 * ⚠️ NO lleva `disabled:opacity-50`, a diferencia de la constante homónima de `vacacionesForm`.
 * El `<select>` de área SÍ se deshabilita mientras no haya empresa elegida, así que agregarlo
 * sería un cambio visible. Se movió tal cual estaba.
 */
export function validateVacante(form: VacanteFormData): VacanteFormErrors {
  const errors: VacanteFormErrors = {}
  if (!form.empresa_id) errors.empresa_id = "La empresa es requerida"
  if (!form.titulo.trim()) errors.titulo = "El título es requerido"
  if (!form.area_id) errors.area_id = "El área es requerida"
  if (!form.tipo_contrato) errors.tipo_contrato = "El tipo de contrato es requerido"
  return errors
}

/** Payload del alta. Los cuatro campos que hoy acepta el POST, ni uno más. */
export function payloadVacante(form: VacanteFormData): VacanteCreate {
  return {
    empresa_id: form.empresa_id,
    titulo: form.titulo.trim(),
    area_id: form.area_id,
    tipo_contrato: form.tipo_contrato,
  }
}
