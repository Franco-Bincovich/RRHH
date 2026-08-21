/**
 * La forma y las reglas del formulario de empresa: qué campos tiene, cómo arranca vacío y qué
 * hace que no se pueda guardar.
 *
 * Sale de `EmpresaModal.tsx`, que estaba en **226 líneas contra un límite de 150** —deuda anotada
 * en CLAUDE.md desde antes de esta tanda— y que al sumarle el patrón de modal de formulario del
 * bloque B (`patron="formulario"`, la línea de consecuencia y el banner de errores) se iba a 241.
 * El corte es por responsabilidad y no por líneas: acá vive la DEFINICIÓN del formulario, en
 * `EmpresaFormFields.tsx` su render, y en el modal el ciclo de vida (abrir, guardar, cerrar).
 * Molde: `areaForm.ts` + `AreaFormFields.tsx`, que ya resolvieron exactamente esto.
 */
export type EmpresaFormData = {
  nombre: string
  razon_social: string
  cuit: string
  direccion: string
  telefono: string
  email: string
  logo_url: string
}

export type EmpresaFormErrors = Partial<Record<keyof EmpresaFormData, string>>

export const EMPTY_EMPRESA: EmpresaFormData = {
  nombre: "",
  razon_social: "",
  cuit: "",
  direccion: "",
  telefono: "",
  email: "",
  logo_url: "",
}

const CUIT_RE = /^\d{2}-\d{8}-\d{1}$/

/**
 * Las dos únicas reglas que impiden guardar. El CUIT se valida **sólo si viene cargado**: es
 * opcional, y exigir el formato a un campo vacío convertiría un dato que puede faltar en un
 * bloqueo.
 */
export function validarEmpresa(form: EmpresaFormData): EmpresaFormErrors {
  const errors: EmpresaFormErrors = {}
  if (!form.nombre.trim()) {
    errors.nombre = "El nombre es requerido"
  }
  if (form.cuit.trim() && !CUIT_RE.test(form.cuit.trim())) {
    errors.cuit = "Formato inválido — debe ser XX-XXXXXXXX-X"
  }
  return errors
}
