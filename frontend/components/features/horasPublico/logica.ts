import { ApiError } from "@/services/api"
import type { CargaHorasBody, CargaLicenciaBody } from "@/types/horasPublico"

/**
 * Toda la lógica de la pantalla pública que se puede decidir SIN un DOM.
 *
 * Vive suelta a propósito: el proyecto corre vitest **sin jsdom**, así que los `useEffect` no se
 * ejecutan y `renderToStaticMarkup` no puede clickear nada. Lo único que se prueba de verdad es
 * esto — por eso todo lo que sea una regla y no un `<div>` termina acá.
 */

/** Tope y ventana del backend, espejados para poder avisar ANTES de mandar. */
export const MAX_HORAS_DIA = 12
export const DIAS_HACIA_ATRAS = 30
/** Jornada que el backend asume cuando el empleado no tiene `horas_contrato`. */
export const HORAS_ASUMIDAS = 8

export type Modo = "horas" | "licencia"

export interface FormHoras {
  fecha: string
  horas: string
  modalidad: string
  cliente_id: string
  proyecto_texto: string
  tarea_texto: string
  descripcion: string
}

export interface FormLicencia {
  fecha_desde: string
  fecha_hasta: string
  observaciones: string
}

export const FORM_HORAS_VACIO: FormHoras = {
  fecha: "", horas: "", modalidad: "", cliente_id: "",
  proyecto_texto: "", tarea_texto: "", descripcion: "",
}
export const FORM_LICENCIA_VACIO: FormLicencia = {
  fecha_desde: "", fecha_hasta: "", observaciones: "",
}

/**
 * Deja solo los dígitos del DNI: el usuario escribe "12.345.678" o "12-345-678" y el backend
 * compara contra `empleados.dni`, que está guardado sin separadores. Sin esto, un DNI correcto
 * tipeado como se lee en el documento sale rechazado.
 */
export function normalizarDni(valor: string): string {
  return (valor ?? "").replace(/\D/g, "")
}

/** Errores por campo del formulario de horas; `{}` si está listo para enviar. */
export function validarHoras(f: FormHoras): Partial<Record<keyof FormHoras, string>> {
  const e: Partial<Record<keyof FormHoras, string>> = {}
  if (!f.fecha) e.fecha = "Elegí la fecha"
  if (!f.cliente_id) e.cliente_id = "Elegí el cliente"
  if (!f.modalidad) e.modalidad = "Elegí la modalidad"
  const horas = Number(f.horas)
  if (!f.horas.trim()) e.horas = "Ingresá las horas"
  else if (Number.isNaN(horas) || horas <= 0) e.horas = "Tiene que ser mayor a 0"
  else if (horas > MAX_HORAS_DIA) e.horas = `El máximo por día es ${MAX_HORAS_DIA}`
  return e
}

/** Errores del formulario de licencia; `{}` si está listo. */
export function validarLicencia(f: FormLicencia): Partial<Record<keyof FormLicencia, string>> {
  const e: Partial<Record<keyof FormLicencia, string>> = {}
  if (!f.fecha_desde) e.fecha_desde = "Elegí desde cuándo"
  if (!f.fecha_hasta) e.fecha_hasta = "Elegí hasta cuándo"
  if (f.fecha_desde && f.fecha_hasta && f.fecha_hasta < f.fecha_desde) {
    e.fecha_hasta = "No puede ser anterior al inicio"
  }
  return e
}

export function puedeEnviar(modo: Modo, h: FormHoras, l: FormLicencia): boolean {
  return Object.keys(modo === "horas" ? validarHoras(h) : validarLicencia(l)).length === 0
}

/** `min`/`max` del input date: la ventana de 30 días que el backend impone. */
export function ventanaFechas(hoy: Date): { min: string; max: string } {
  const iso = (d: Date) => d.toISOString().slice(0, 10)
  const desde = new Date(hoy)
  desde.setDate(desde.getDate() - DIAS_HACIA_ATRAS)
  return { min: iso(desde), max: iso(hoy) }
}

/** Body de la carga de horas. Los opcionales vacíos NO viajan: "" no es un dato. */
export function bodyHoras(token: string, f: FormHoras, idempotencia: string): CargaHorasBody {
  const opcional = (v: string) => (v.trim() ? v.trim() : undefined)
  return {
    token, fecha: f.fecha, horas: Number(f.horas),
    modalidad: f.modalidad as CargaHorasBody["modalidad"], cliente_id: f.cliente_id,
    proyecto_texto: opcional(f.proyecto_texto), tarea_texto: opcional(f.tarea_texto),
    descripcion: opcional(f.descripcion), idempotencia,
  }
}

export function bodyLicencia(token: string, f: FormLicencia): CargaLicenciaBody {
  return {
    token, fecha_desde: f.fecha_desde, fecha_hasta: f.fecha_hasta,
    observaciones: f.observaciones.trim() || undefined,
  }
}

/**
 * 🔴 ¿ESTE ERROR MATÓ LA SESIÓN? Se decide por el `code`, NO por el status.
 *
 * Los DOS rechazos del flujo son 401: `SESION_INVALIDA` (el token venció o no sirve) e
 * `IDENTIFICACION_INVALIDA` (el DNI no identificó a nadie). Mirar el status los confundiría y
 * un DNI mal tipeado borraría una sesión que estaba perfecta.
 */
export function esSesionMuerta(e: unknown): boolean {
  return e instanceof ApiError && e.code === "SESION_INVALIDA"
}

/** El mensaje del backend, tal cual. Ver el encabezado de `services/horasPublico.ts`. */
export function mensajeDeError(e: unknown): string {
  return e instanceof ApiError ? e.message : "No pudimos conectarnos. Revisá tu internet."
}

/**
 * 🔴 EL CASO QUE EL FRONT NO PUEDE DISTINGUIR, Y QUÉ SE MUESTRA IGUAL.
 *
 * El backend usa RECHAZO ÚNICO en la identificación: "no existe", "está de baja", "su empresa no
 * tiene clientes", "el dni figura en dos empresas" y "superó el límite de intentos" salen con el
 * MISMO code y el MISMO mensaje, a propósito, para no darle un oráculo a alguien probando DNIs.
 * Verificado contra `services/identificacion_service.py::_RECHAZO`.
 *
 * Consecuencia práctica: HOY hay 0 clientes cargados, y con 0 clientes la identificación rechaza
 * a TODO el padrón — pero desde acá se ve igual que un DNI mal tipeado. Mandar a la persona a
 * "revisar su documento" sería mandarla a buscar un problema que no tiene.
 *
 * La salida que NO rompe la garantía: un complemento FIJO, que se muestra SIEMPRE junto al
 * rechazo y no depende de la respuesta. Al ser constante no distingue nada —no filtra en qué
 * caso está quien pregunta— y a la vez le da a un empleado real la única acción que le sirve.
 */
export const AYUDA_IDENTIFICACION =
  "Si el número es correcto y sigue sin funcionar, avisale a Capital Humano: puede que tu " +
  "usuario todavía no esté habilitado."
