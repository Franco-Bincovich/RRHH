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
 * 🔴 SIN EMPRESA (migración 108). El alta manda solo el nombre. La versión anterior de este
 * archivo mandaba `empresa_id: getEmpresaActivaId() ?? ""`, y como `null` es el valor NORMAL del
 * selector del sidebar en "Todas las empresas" (el default: `setEmpresaActivaId(null)` BORRA la
 * clave de localStorage), el alta salía con `empresa_id: ""` y Pydantic la rechazaba con 422 —
 * el alta de clientes estuvo rota en producción, siempre. El `?? ""` no se "arregló": desapareció
 * junto con el campo, porque el cliente dejó de pertenecer a una empresa.
 */

export const MAX_NOMBRE = 120

export interface FormCliente {
  nombre: string
}

export interface ErroresCliente {
  nombre?: string
}

/** Error de nombre, o "" si está bien. */
export function validarNombre(nombre: string): string {
  if (!nombre.trim()) return "El nombre es requerido"
  if (nombre.trim().length > MAX_NOMBRE) return `Máximo ${MAX_NOMBRE} caracteres`
  return ""
}

/** Errores del formulario. Objeto vacío = se puede mandar. */
export function validarCliente(form: FormCliente): ErroresCliente {
  const errores: ErroresCliente = {}
  const nombre = validarNombre(form.nombre)
  if (nombre) errores.nombre = nombre
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
  const errores = validarCliente(form)
  if (Object.keys(errores).length > 0) return errores
  if (cliente) await updateCliente(cliente.id, { nombre: form.nombre.trim() })
  else await createCliente({ nombre: form.nombre.trim() })
  return null
}
