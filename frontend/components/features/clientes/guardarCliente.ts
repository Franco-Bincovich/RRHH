import { createCliente, updateCliente } from "@/services/clientes"
import type { Cliente } from "@/types/cliente"

/**
 * La decisión de guardar un cliente: validar primero y mandar SOLO si pasa.
 *
 * 🔴 POR QUÉ ESTO VIVE ACÁ Y NO EN EL CUERPO DE `ClienteModal`. El modal usa `Dialog` de Radix,
 * que monta por PORTAL: con vitest sin jsdom, `renderToStaticMarkup(<ClienteModal/>)` devuelve
 * "". Un test de ese componente pasaría con el formulario entero borrado, así que la decisión
 * que hay que poder desmentir tiene que ser una función suelta. Mismo motivo por el que ya
 * estaban afuera `cargarClientes` y `mensajeDeError`.
 *
 * 🔴 Y ES LA ÚNICA PUERTA A `createCliente` DESDE ESTA PANTALLA. Que el modal no importe
 * `createCliente` es lo que hace que el test de acá hable del comportamiento real y no de un
 * helper paralelo: si el modal pudiera llamar al service por su cuenta, este archivo sería una
 * opinión sobre lo que el modal debería hacer. Hay un test estructural que lo verifica.
 *
 * EL BUG QUE CIERRA: el modal mandaba `empresa_id: getEmpresaActivaId() ?? ""`, y `null` es el
 * valor normal del selector del sidebar en "Todas las empresas" (el default: `setEmpresaActivaId(null)`
 * BORRA la clave de localStorage). O sea que el alta mandaba `empresa_id: ""` y Pydantic lo
 * rechazaba con 422 — `ClienteCreate.empresa_id` es `UUID` obligatorio, a propósito: crear es una
 * ACCIÓN y la empresa sale del formulario, no del header (Vista vs Acción).
 */

export const MAX_NOMBRE = 120

export interface FormCliente {
  nombre: string
  /** UUID de la empresa DUEÑA. `""` = el sidebar está en "Todas las empresas". */
  empresaId: string
}

export interface ErroresCliente {
  nombre?: string
  empresa?: string
}

/** Error de nombre, o "" si está bien. */
export function validarNombre(nombre: string): string {
  if (!nombre.trim()) return "El nombre es requerido"
  if (nombre.trim().length > MAX_NOMBRE) return `Máximo ${MAX_NOMBRE} caracteres`
  return ""
}

/**
 * Errores del formulario. Objeto vacío = se puede mandar.
 *
 * La empresa se exige SOLO en el alta, igual que en `ItemModal` y `CapacitacionModal`: no está
 * en `ClienteUpdate` a propósito —mudar un cliente de empresa dejaría las horas ya cargadas
 * imputadas a una sociedad que no es la que facturó—, así que en la edición no hay nada que
 * validar. Exigirla ahí rompería la edición sin motivo.
 */
export function validarCliente(form: FormCliente, isEdit: boolean): ErroresCliente {
  const errores: ErroresCliente = {}
  const nombre = validarNombre(form.nombre)
  if (nombre) errores.nombre = nombre
  if (!isEdit && !form.empresaId) errores.empresa = "Requerido"
  return errores
}

/**
 * Valida y guarda. Alta o edición según venga `cliente`.
 *
 * @returns Los errores si NO guardó, o `null` si guardó. Un `AppError` del backend (por ejemplo
 *   CLIENTE_DUPLICADO) sale como excepción y lo traduce `mensajeDeError`.
 */
export async function guardarCliente(
  form: FormCliente, cliente?: Cliente,
): Promise<ErroresCliente | null> {
  const errores = validarCliente(form, Boolean(cliente))
  if (Object.keys(errores).length > 0) return errores
  if (cliente) await updateCliente(cliente.id, { nombre: form.nombre.trim() })
  // Sin `?? ""`: `empresaId` ya pasó la validación, así que acá sólo puede ser un UUID real.
  else await createCliente({ empresa_id: form.empresaId, nombre: form.nombre.trim() })
  return null
}
