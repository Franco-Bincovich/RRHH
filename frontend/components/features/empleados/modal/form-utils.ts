import { isoLocal } from "@/components/features/shared/fechas"
import { validarEmail } from "@/components/features/shared/validacionEmail"
import type { Empleado, EmpleadoCreate, EstadoAlta } from "@/types/empleado"
import type { FormData, FormErrors } from "./_constants"

/**
 * La fecha de HOY en ISO, **en hora local y no en UTC**.
 *
 * 🔴 `new Date().toISOString().slice(0, 10)` es el atajo obvio y está mal acá: `toISOString`
 * convierte a UTC, y en Argentina (UTC-3) desde las 21:00 devuelve el día SIGUIENTE. O sea que
 * un alta cargada de noche con fecha de ingreso "mañana" se leería como "hoy" y nacería activa.
 * Es un bug de tres horas por día, que es la peor clase: no se reproduce en la sesión que lo
 * escribe.
 *
 * La cuenta vive en `shared/fechas.ts::isoLocal` desde que apareció el segundo llamador (la
 * ventana de fechas de la pantalla pública de carga de horas). Esto es esa función sin parámetro.
 */
export function hoyISO(): string {
  return isoLocal(new Date())
}

/**
 * Con qué estado NACE un legajo según su fecha de ingreso.
 *
 * 🔴 EL DEFAULT NO DEBERÍA OBLIGAR A PENSAR: si la persona todavía no entró, lo correcto es
 * `preingreso`, y esperar que el usuario se acuerde de cambiarlo es exactamente cómo se llegó al
 * bug que esto cierra (un alta con fecha futura nacía `activa` y entraba en la dotación del mes
 * sin que la persona hubiera pisado la oficina). El usuario puede cambiarlo igual: es un default,
 * no una regla.
 *
 * Sin fecha cargada devuelve `"activo"`: es el caso de un formulario recién abierto, y suponer
 * "todavía no ingresó" antes de que el usuario diga nada sería adivinar al revés.
 *
 * ⚠️ EL DEFAULT TIENE QUE PODER PERDERSE, y por eso el hook lleva un flag `estadoTocado` en vez
 * de derivar el estado en cada render. Si se derivara siempre, un usuario que elige a propósito
 * "Ya está trabajando" para alguien con fecha futura —caso real: la persona ya firmó y ya trabaja
 * en otra sede— vería su elección revertida al corregir cualquier cosa de la fecha, y no habría
 * forma de dar esa alta. Con el flag, la derivación manda hasta que el usuario opina y después
 * se calla.
 */
export function estadoSegunFecha(fechaIngreso: string, hoy = hoyISO()): EstadoAlta {
  return fechaIngreso && fechaIngreso > hoy ? "preingreso" : "activo"
}

/**
 * Validación pura del form. Devuelve el mapa de errores (vacío = válido).
 *
 * 🔴 CADA MENSAJE DICE QUÉ HACER, NO QUÉ ESTÁ MAL. Es el segundo nivel de la validación del
 * patrón de modal de formulario (`docs/SISTEMA-DE-DISENO.md` §3): "mensaje de 11px que dice **qué
 * corregir**, no 'campo inválido'".
 *
 * Hasta el 19/8/2026 seis de los ocho decían la misma frase con distinto sustantivo —"La empresa
 * es requerida", "El nombre es requerido", "El área es requerida"— y eso **no le agrega nada al
 * asterisco rojo que el campo ya tiene al lado del label**: el usuario ya sabe que es obligatorio;
 * lo que no sabe es qué escribir ahí. El peor de todos era "El email no es válido", que es el
 * ejemplo textual que el sistema de diseño usa para explicar el problema: no dice si falta el
 * arroba, si sobra un espacio o si el dominio está incompleto.
 *
 * Los dos que ya estaban bien —"Agregá al menos un rol" y el de las horas— se dejaron como
 * estaban: son exactamente lo que la regla pide.
 *
 * ⚠️ Hay un test que barre estos textos contra una lista de palabras prohibidas
 * ("inválido", "requerido", "error"). No es cosmético: son las tres formas de escribir un mensaje
 * que no ayuda, y sin el barrido el próximo campo nuevo vuelve a la fórmula vieja.
 */
export function validate(form: FormData, isEdit: boolean): FormErrors {
  const errors: FormErrors = {}
  if (!isEdit && !form.empresa_id) errors.empresa_id = "Elegí de qué empresa va a depender el legajo"
  if (!form.nombre.trim()) errors.nombre = "Escribí el nombre tal como figura en el documento"
  if (!form.apellido.trim()) errors.apellido = "Escribí el apellido tal como figura en el documento"
  // 🔑 LOS DOS MENSAJES SON LOS MISMOS DE ANTES: se movieron a `shared/validacionEmail.ts` tal
  // cual, porque esta pantalla es la que los tenía bien y es el molde. Lo que cambió es que ahora
  // los comparte con los otros cuatro formularios que piden un email — había TRES copias del
  // regex con TRES mensajes distintos, y dos formularios que no validaban nada.
  const errorEmail = validarEmail(form.email_corporativo)
  if (errorEmail) errors.email_corporativo = errorEmail
  if (!form.area_id) errors.area_id = "Elegí el área en la que va a trabajar. Si no está en la lista, creala primero en Áreas"
  if (form.roles.length === 0) errors.roles = "Agregá al menos un rol"
  if (!form.fecha_ingreso) errors.fecha_ingreso = "Elegí el día en que la persona empieza a trabajar"
  if (form.horas_contrato.trim() && !/^\d+$/.test(form.horas_contrato.trim())) {
    errors.horas_contrato = "Las horas tienen que ser un número entero"
  }
  return errors
}

/** Mapea un Empleado existente al estado del form (modo edición). */
export function toFormData(empleado: Empleado): FormData {
  return {
    empresa_id: "",
    // 🔴 SIEMPRE "activo", y NO el estado real del empleado. En edición este campo no se
    // renderiza ni se envía (`buildPayload` no lo incluye), así que el valor es inerte: ponerle
    // el estado real sugeriría que editarlo hace algo. Un legajo en `baja` o `licencia` ni
    // siquiera tiene un valor representable acá — `EstadoAlta` son dos, no cinco.
    estado: "activo",
    nombre: empleado.nombre,
    apellido: empleado.apellido,
    email_corporativo: empleado.email_corporativo,
    area_id: empleado.area_id,
    roles: empleado.roles ?? [],
    modalidad_trabajo: empleado.modalidad_trabajo,
    tipo_contrato: empleado.tipo_contrato,
    fecha_ingreso: empleado.fecha_ingreso,
    telefono: empleado.telefono ?? "",
    fecha_nacimiento: empleado.fecha_nacimiento ?? "",
    dni: empleado.dni ?? "",
    cuil: empleado.cuil ?? "",
    legajo: empleado.legajo ?? "",
    manager_id: empleado.manager_id ?? "",
    dias_vacaciones_asignados: String(empleado.dias_vacaciones_asignados ?? 14),
    tipo_documento: empleado.tipo_documento ?? "",
    sexo: empleado.sexo ?? "",
    telefono_alternativo: empleado.telefono_alternativo ?? "",
    email_personal: empleado.email_personal ?? "",
    domicilio: empleado.domicilio ?? "",
    domicilio_calle: empleado.domicilio_calle ?? "",
    domicilio_numero: empleado.domicilio_numero ?? "",
    domicilio_piso_depto: empleado.domicilio_piso_depto ?? "",
    domicilio_localidad: empleado.domicilio_localidad ?? "",
    domicilio_provincia: empleado.domicilio_provincia ?? "",
    domicilio_cp: empleado.domicilio_cp ?? "",
    estudios: empleado.estudios ?? "",
    ubicacion: empleado.ubicacion ?? "",
    turno: empleado.turno ?? "",
    horas_contrato: empleado.horas_contrato != null ? String(empleado.horas_contrato) : "",
    seniority: empleado.seniority ?? "",
    categoria: empleado.categoria ?? "",
    referido: empleado.referido ?? "",
    es_lider: empleado.es_lider ?? false,
  }
}

/**
 * Arma el payload de la API a partir del form (sin empresa_id; lo agrega el create).
 *
 * 🔴 `estado` NO SALE DE ACÁ, y la omisión es la que sostiene la regla de A3. Este payload lo
 * usan los DOS caminos —crear y editar—: si el estado viajara desde acá, una edición cualquiera
 * podría devolver a `activo` a alguien que está en `licencia`, salteándose la guarda de
 * `/activar` (que exige que la fecha de ingreso ya haya ocurrido). Lo agrega el `create` del
 * modal, que es el único lugar donde elegir un estado inicial tiene sentido.
 */
export function buildPayload(form: FormData): Omit<EmpleadoCreate, "empresa_id" | "estado"> {
  return {
    nombre: form.nombre,
    apellido: form.apellido,
    email_corporativo: form.email_corporativo,
    area_id: form.area_id,
    roles: form.roles,
    modalidad_trabajo: form.modalidad_trabajo,
    tipo_contrato: form.tipo_contrato,
    fecha_ingreso: form.fecha_ingreso,
    telefono: form.telefono || undefined,
    fecha_nacimiento: form.fecha_nacimiento || undefined,
    dni: form.dni || undefined,
    cuil: form.cuil || undefined,
    legajo: form.legajo || undefined,
    manager_id: form.manager_id || null,  // null explícito = "Sin superior" (limpiar); undefined = no tocar
    dias_vacaciones_asignados: form.dias_vacaciones_asignados
      ? parseInt(form.dias_vacaciones_asignados, 10)
      : undefined,
    tipo_documento: form.tipo_documento || undefined,
    sexo: form.sexo || undefined,
    telefono_alternativo: form.telefono_alternativo || undefined,
    email_personal: form.email_personal || undefined,
    domicilio: form.domicilio || undefined,
    domicilio_calle: form.domicilio_calle || undefined,
    domicilio_numero: form.domicilio_numero || undefined,
    domicilio_piso_depto: form.domicilio_piso_depto || undefined,
    domicilio_localidad: form.domicilio_localidad || undefined,
    domicilio_provincia: form.domicilio_provincia || undefined,
    domicilio_cp: form.domicilio_cp || undefined,
    estudios: form.estudios || undefined,
    ubicacion: form.ubicacion || undefined,
    turno: form.turno || undefined,
    horas_contrato: form.horas_contrato ? parseInt(form.horas_contrato, 10) : undefined,
    seniority: form.seniority || undefined,
    categoria: form.categoria || undefined,
    referido: form.referido || undefined,
    es_lider: form.es_lider,
  }
}
