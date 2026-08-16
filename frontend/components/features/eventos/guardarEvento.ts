import { createEvento, updateEvento } from "@/services/eventos"
import type { Evento } from "@/types/evento"

/**
 * La decisión de guardar un evento: validar primero y mandar SOLO si pasa.
 *
 * 🔴 POR QUÉ ESTO VIVE ACÁ Y NO EN EL CUERPO DE `EventoModal`. El modal usa `Dialog` de Radix,
 * que monta por PORTAL: con vitest sin jsdom, `renderToStaticMarkup(<EventoModal/>)` devuelve
 * "". Un test de ese componente pasaría con el formulario entero borrado, así que la decisión
 * que hay que poder desmentir tiene que ser una función suelta. Molde: `guardarCliente.ts`.
 *
 * 🔴 `diasAviso` VACÍO NO ES CERO. El campo llega como string desde el `<input type="number">`,
 * y `Number("")` es `0` — que acá significaría "avisar el mismo día", un valor legítimo y muy
 * distinto de "no lo toqué". Vacío se traduce a `undefined` y el backend aplica el default de la
 * empresa; cero se manda como cero. Es el mismo `Number("")` que ya mordió en `_campos.tsx`.
 */

export const MAX_NOMBRE = 120
export const MAX_DESCRIPCION = 1000
// Espejo del CHECK `eventos_agenda_dias_aviso_check` y del schema Pydantic.
export const MIN_DIAS_AVISO = 0
export const MAX_DIAS_AVISO = 365

export interface FormEvento {
  nombre: string
  fecha: string
  descripcion: string
  /** Como viene del input: texto. "" = usar el default de la empresa. */
  diasAviso: string
  esPublica: boolean
}

export interface ErroresEvento {
  nombre?: string
  fecha?: string
  descripcion?: string
  diasAviso?: string
}

/** `undefined` si el campo quedó vacío; el número si se cargó. No confunde vacío con 0. */
export function diasAvisoNumero(valor: string): number | undefined {
  const limpio = valor.trim()
  if (!limpio) return undefined
  const n = Number(limpio)
  return Number.isFinite(n) ? n : undefined
}

/** Errores del formulario. Objeto vacío = se puede mandar. */
export function validarEvento(form: FormEvento): ErroresEvento {
  const errores: ErroresEvento = {}
  if (!form.nombre.trim()) errores.nombre = "El nombre es requerido"
  else if (form.nombre.trim().length > MAX_NOMBRE) errores.nombre = `Máximo ${MAX_NOMBRE} caracteres`
  if (!form.fecha) errores.fecha = "La fecha es requerida"
  if (form.descripcion.length > MAX_DESCRIPCION) {
    errores.descripcion = `Máximo ${MAX_DESCRIPCION} caracteres`
  }
  // Se valida el TEXTO, no el número: "abc" da NaN y `diasAvisoNumero` lo trataría como vacío,
  // o sea que se guardaría en silencio con el default de la empresa en vez de avisar.
  const crudo = form.diasAviso.trim()
  if (crudo) {
    const n = Number(crudo)
    if (!Number.isInteger(n) || n < MIN_DIAS_AVISO || n > MAX_DIAS_AVISO) {
      errores.diasAviso = `Entre ${MIN_DIAS_AVISO} y ${MAX_DIAS_AVISO} días`
    }
  }
  return errores
}

/**
 * Valida y guarda. Alta o edición según venga `evento`.
 *
 * @returns Los errores si NO guardó, o `null` si guardó. Un `AppError` del backend sale como
 *   excepción y lo traduce `mensajeDeError`.
 */
export async function guardarEvento(
  form: FormEvento, evento?: Evento,
): Promise<ErroresEvento | null> {
  const errores = validarEvento(form)
  if (Object.keys(errores).length > 0) return errores
  const datos = {
    nombre: form.nombre.trim(),
    fecha: form.fecha,
    descripcion: form.descripcion.trim(),
    dias_aviso: diasAvisoNumero(form.diasAviso),
    es_publica: form.esPublica,
  }
  if (evento) await updateEvento(evento.id, datos)
  else await createEvento(datos)
  return null
}
