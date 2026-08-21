import { hoyISO } from "@/components/features/empleados/modal/form-utils"
import { ApiError } from "@/services/api"
import { createRecategorizacion, updateRecategorizacion } from "@/services/recategorizaciones"
import type {
  Recategorizacion, RecategorizacionCreate, RecategorizacionUpdate,
} from "@/types/recategorizacion"

/**
 * La decisión de guardar una recategorización: validar primero y mandar SOLO si pasa.
 *
 * 🔴 POR QUÉ VIVE ACÁ Y NO EN EL CUERPO DEL MODAL. El modal monta por PORTAL (`Dialog` de
 * base-ui): con vitest sin jsdom, `renderToStaticMarkup(<RecategorizacionModal/>)` devuelve `""`,
 * así que un test de ese componente pasaría con el formulario entero borrado. Molde:
 * `guardarCliente.ts` y `guardarPerfil.ts`.
 *
 * 🔴 NO HAY `borrarRecategorizacion` NI LO VA A HABER: el backend no publica DELETE. La
 * corrección de una fila mal cargada es EDITARLA. Ver `services/recategorizaciones.ts`.
 */

/** Espejo de `MAX_MOTIVO` de `schemas/recategorizacion.py`. Es una línea de explicación, no notas. */
export const MAX_MOTIVO = 500

export interface FormRecategorizacion {
  empleadoId: string
  fechaEfectiva: string
  rolNuevo: string
  seniorityNueva: string
  categoriaNueva: string
  motivo: string
  /** Monto en pesos, opcional. Viaja como STRING: el backend lo recibe como `Decimal`. */
  impactoSalarial: string
}

/**
 * Con qué valores nace el formulario.
 *
 * 🔴 `fechaEfectiva` ARRANCA EN HOY, no vacía: el caso normal es registrar un cambio que rige
 * desde hoy, y una fecha vacía obligaría a completarla siempre. Es EDITABLE hacia atrás — el
 * aviso de lo que eso implica lo pone el modal.
 *
 * ⚠️ Los tres campos nuevos nacen VACÍOS incluso en la edición, y eso NO es un bug: `rol_nuevo`
 * en `null` significa "este cambio no tocó el rol", así que precargarlo con el valor anterior
 * convertiría una edición cualquiera en un cambio de rol que nadie pidió.
 */
export function formInicial(original?: Recategorizacion): FormRecategorizacion {
  return {
    empleadoId: original?.empleado_id ?? "",
    fechaEfectiva: original?.fecha_efectiva ?? hoyISO(),
    rolNuevo: original?.rol_nuevo ?? "",
    seniorityNueva: original?.seniority_nueva ?? "",
    categoriaNueva: original?.categoria_nueva ?? "",
    motivo: original?.motivo ?? "",
    impactoSalarial: original?.impacto_salarial ?? "",
  }
}

export interface ErroresRecategorizacion {
  empleadoId?: string
  motivo?: string
  /** Espejo del 422 `RECATEGORIZACION_SIN_CAMBIOS`. No cuelga de un campo: cuelga de los tres. */
  cambios?: string
}

/**
 * Errores del formulario. Objeto vacío = se puede mandar.
 *
 * 🔴 LA REGLA DE "ALGO TIENE QUE CAMBIAR" SE VALIDA ACÁ **Y** EN EL BACKEND **Y** EN LA BASE, y
 * las tres capas hacen falta: el CHECK `recategorizaciones_algo_cambia_check` (migración 117) es
 * la garantía, el 422 del service es el mensaje legible, y esto evita el viaje a la red para un
 * formulario que ya se sabe incompleto. Si esta capa se borrara, el usuario vería el mismo texto
 * pero después de un round-trip.
 *
 * ⚠️ `empleadoId` se valida SOLO en el alta: en la edición el selector está deshabilitado porque
 * el backend no acepta cambiar de persona (ver `RecategorizacionUpdate`).
 */
export function validarRecategorizacion(
  form: FormRecategorizacion, esEdicion = false,
): ErroresRecategorizacion {
  const errores: ErroresRecategorizacion = {}
  if (!esEdicion && !form.empleadoId) errores.empleadoId = "Elegí a quién se recategoriza"
  const motivo = form.motivo.trim()
  if (!motivo) errores.motivo = "El motivo es requerido"
  else if (motivo.length > MAX_MOTIVO) errores.motivo = `Máximo ${MAX_MOTIVO} caracteres`
  if (!form.rolNuevo.trim() && !form.seniorityNueva.trim() && !form.categoriaNueva.trim()) {
    errores.cambios = "Indicá al menos un valor nuevo: rol, seniority o categoría"
  }
  return errores
}

/**
 * El body que se manda.
 *
 * 🔴 LOS `*_anterior` NO ESTÁN, Y ESA AUSENCIA ES LA DECISIÓN CENTRAL DEL MÓDULO. Los completa el
 * backend leyendo la última recategorización previa a `fecha_efectiva`. Mandarlos desde acá —aun
 * "por completitud"— permitiría escribir un histórico que no concuerda con el anterior, que es
 * justo lo que la tabla existe para impedir. El formulario tampoco los pide.
 *
 * ⚠️ LOS CAMPOS VACÍOS SE OMITEN, no se mandan como `""`. Un `""` en `rol_nuevo` se guardaría
 * como cadena vacía y contaría como "cambió el rol" para el CHECK; y en `impacto_salarial` sería
 * un `Decimal("")` → 422. Omitirlos significa "no lo toques", que es el contrato del PUT.
 *
 * ⚠️ CONSECUENCIA CONOCIDA, no un descuido: por eso mismo **no se puede VACIAR un impacto ya
 * cargado desde la pantalla**. El PUT del backend arma el patch con `exclude_none` y `Decimal` no
 * acepta cadena vacía, así que no hay valor que mande "borralo". Se corrige cargando el monto
 * correcto. Si algún día hace falta vaciarlo, es un cambio de backend, no de acá.
 */
function armarPayload(form: FormRecategorizacion): RecategorizacionUpdate {
  const opcional = (v: string) => (v.trim() ? v.trim() : undefined)
  return {
    fecha_efectiva: form.fechaEfectiva || undefined,
    rol_nuevo: opcional(form.rolNuevo),
    seniority_nueva: opcional(form.seniorityNueva),
    categoria_nueva: opcional(form.categoriaNueva),
    motivo: form.motivo.trim(),
    impacto_salarial: opcional(form.impactoSalarial),
  }
}

/**
 * Valida y guarda. Alta o edición según venga `recategorizacion`.
 *
 * @returns Los errores si NO guardó, o `null` si guardó. Un `AppError` del backend
 *   (RECATEGORIZACION_SIN_CAMBIOS 422, EMPLEADO_NOT_FOUND 404) sale como excepción.
 */
export async function guardarRecategorizacion(
  form: FormRecategorizacion, recategorizacion?: Recategorizacion,
): Promise<ErroresRecategorizacion | null> {
  const errores = validarRecategorizacion(form, Boolean(recategorizacion))
  if (Object.keys(errores).length > 0) return errores
  const body = armarPayload(form)
  if (recategorizacion) {
    await updateRecategorizacion(recategorizacion.id, body)
  } else {
    // `empleado_id` va SOLO en el alta: el PUT no lo acepta y mandarlo sería pedirle al backend
    // algo que rechaza. No se cambia de persona.
    await createRecategorizacion({ ...body, empleado_id: form.empleadoId } as RecategorizacionCreate)
  }
  return null
}

/**
 * Mensaje a mostrar cuando falla el guardado.
 *
 * 🔴 EL MENSAJE DEL BACKEND SE CONSERVA TAL CUAL. Los dos errores de negocio que este formulario
 * produce —`RECATEGORIZACION_SIN_CAMBIOS` (422) y `EMPLEADO_NOT_FOUND` (404)— vienen redactados
 * para alguien de Capital Humano y dicen qué hacer. Un genérico deja a la persona apretando
 * "Guardar" sin entender por qué no pasa nada, y "Intentá de nuevo" sería además el consejo
 * equivocado: reintentar lo mismo nunca funciona. El genérico queda para lo que NO es un error de
 * la API (red caída), donde reintentar sí es lo razonable.
 */
export function mensajeDeError(e: unknown): string {
  return e instanceof ApiError ? e.message : "No se pudo guardar. Intentá de nuevo."
}
