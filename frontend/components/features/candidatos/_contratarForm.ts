import { validarEmail } from "@/components/features/shared/validacionEmail"

/**
 * La validación del formulario de contratación (candidato → legajo).
 *
 * 🔴 POR QUÉ ES UN ARCHIVO APARTE Y NO UN `if` DENTRO DEL BOTÓN. El 24/8/2026 esta pantalla creó
 * un legajo con el email corporativo **"a"**, y la causa no fue un olvido puntual: el componente
 * copió el molde de `EliminarCandidatoButton`, que es un BOTÓN DE CONFIRMACIÓN y no un
 * formulario. Un botón de confirmación no tiene capa de validación — tiene un `disabled` con
 * condiciones de PRESENCIA. Lo que heredó fue eso: `disabled={!email.trim() || roles.length === 0}`,
 * que da verdadero con `"a"`.
 *
 * La salida no es agregarle el `if` que faltaba: es que este formulario tenga la MISMA FORMA que
 * los otros del repo —una función pura `validar(form) → errores por campo`— que es la que
 * `/empleados` ya tenía y por la que ahí sí se validaba. Y de paso es lo único de un modal que
 * esta suite puede probar sin jsdom.
 *
 * 🔑 EL EMAIL SE VALIDA CON EL VALIDADOR COMPARTIDO, no con un regex propio: había TRES copias
 * del mismo regex en el repo con TRES mensajes distintos. Ver `shared/validacionEmail.ts`.
 */

export interface FormContratar {
  email: string
  roles: string[]
  fecha: string
}

export type ErroresContratar = Partial<Record<keyof FormContratar, string>>

/**
 * Los errores por campo, o `{}` si el formulario sirve.
 *
 * @param form  Lo que el usuario cargó.
 * @param hoy   La fecha de hoy en ISO (`YYYY-MM-DD`). **Entra por parámetro y no se calcula acá**
 *              para que el test pueda fijarla: con `new Date()` adentro, el test de "la fecha
 *              pasada se rechaza" pasaría o fallaría según el día en que se corra.
 */
export function validar(form: FormContratar, hoy: string): ErroresContratar {
  const errores: ErroresContratar = {}

  const email = validarEmail(form.email)
  if (email) errores.email = email

  // El mensaje dice qué hacer, no "el campo es requerido" — el asterisco rojo ya dice que es
  // obligatorio; lo que el usuario no sabe es qué escribir. Es el mismo criterio con el que
  // `/empleados` dice "Agregá al menos un rol".
  if (form.roles.length === 0) {
    errores.roles = "Agregá al menos un rol, y presioná Enter para confirmarlo"
  }

  if (!form.fecha) {
    errores.fecha = "Elegí el día acordado de ingreso"
  } else if (form.fecha < hoy) {
    // 🔑 El backend rechaza esto con FECHA_INGRESO_PASADA (400) y su mensaje explica el ciclo
    // entero (contratar registra un acuerdo hacia adelante; si la persona ya entró, el camino es
    // el alta). Acá se evita el viaje, no se reemplaza la barrera.
    errores.fecha = "La fecha tiene que ser de hoy en adelante: contratar registra un acuerdo "
      + "hacia adelante. Si la persona ya entró, el camino es el alta de colaborador"
  }

  return errores
}

export const sinErrores = (e: ErroresContratar): boolean => Object.keys(e).length === 0


/**
 * 🔑 EL MÍNIMO QUE ESTE BOTÓN NECESITA, y no `CandidatoConGrupo`. Se afloja el 25/8/2026 para
 * que el tablero de la vacante —que maneja `types/vacantes.Candidato`, un tipo distinto y más
 * chico— pueda montar el MISMO botón sin convertir nada. Es el mínimo real: el archivo entero
 * usa `id`, `nombre`, `apellido` y `email`; el resto del legajo lo deriva el backend del
 * candidato y de su vacante.
 *
 * ⚠️ LAS DOS CONDICIONES PARA OFRECERLO (etapa `oferta` + estado `activo`) NO SE MUEVEN ACÁ:
 * las aplica quien decide mostrarlo —`CandidatoAcciones` en /candidatos y `PipelineSeleccion` en
 * la ficha de la vacante—, y el backend las revalida igual.
 */
export interface CandidatoContratable {
  id: string
  nombre: string
  apellido: string
  email: string
}
