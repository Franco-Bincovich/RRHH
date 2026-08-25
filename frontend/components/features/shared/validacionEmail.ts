/**
 * LA validación de email del producto. Una sola, con sus dos mensajes.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 POR QUÉ EXISTE — EL MISMO DATO SE VALIDABA EN UNA PANTALLA Y NO EN OTRA
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * El 24/8/2026 el formulario de contratación creó un legajo con el email corporativo **"a"**. No
 * fue un agujero del backend: `POST /api/candidatos/{id}/contratar` no valida el formato (hereda
 * el alta de empleado, que tampoco lo hace — la única defensa es el UNIQUE), así que la única
 * validación que existía vivía en el FRONT… y sólo en tres de los cinco formularios que piden un
 * email.
 *
 * **La causa es de qué molde copió cada uno, y se lee en el código:**
 *   · `/empleados` (`modal/form-utils.ts`) nació con una CAPA de validación —`validate(form)`
 *     devolviendo errores por campo— y por eso valida el formato y da un mensaje que dice qué
 *     corregir.
 *   · `ContratarCandidatoButton` copió el molde de `EliminarCandidatoButton`, que es un BOTÓN DE
 *     CONFIRMACIÓN, no un formulario. Un botón de confirmación no tiene capa de validación: tiene
 *     un `disabled` con condiciones de presencia. Y eso es exactamente lo que heredó —
 *     `disabled={!email.trim() || roles.length === 0}`—, que da verdadero con `"a"`.
 * O sea: **no fue un olvido puntual, fue heredar la idea de validación de un componente que no
 * validaba nada.** Por eso la salida no es agregarle un `if` a ese archivo: es que exista un solo
 * lugar donde vive esta regla y que se lo pueda barrer.
 *
 * ⚠️ HABÍA TRES COPIAS DEL MISMO REGEX (`empleados/modal/form-utils.ts`,
 * `usuarios/CrearUsuarioModal.tsx`, `vacantes/CandidatoModal.tsx`) con TRES mensajes distintos —
 * uno decía "Formato de email inválido", que es el ejemplo textual que el sistema de diseño usa
 * para explicar un mensaje que no ayuda. Mismo modo de falla que las 29 constantes de estilo de
 * `<select>` y los 44 mensajes de error con tres tamaños de letra: una regla copiada entre
 * archivos diverge sola.
 *
 * 🚩 LO QUE ESTE MÓDULO NO ARREGLA, y hay que decirlo: **el backend sigue sin validar el formato**
 * en ninguno de los dos caminos de alta. Un POST directo a la API con `email_corporativo: "a"`
 * entra igual. Cerrarlo es una tanda de backend (un validador en `EmpleadoCreate`), y hasta que
 * ocurra esto es una barrera de UI, no una garantía.
 */

/**
 * El regex. Deliberadamente PERMISIVO: algo, arroba, algo, punto, algo.
 *
 * No se intenta implementar RFC 5322 —el regex "correcto" tiene miles de caracteres y rechaza
 * direcciones válidas que la gente usa— porque el objetivo acá no es certificar que la casilla
 * existe (eso sólo lo dice mandarle un mail), sino atajar el error real que se comete: pegar un
 * nombre suelto, un DNI, o dejar la palabra a medias. `"a"` no pasa; `"a@b.co"` sí, y está bien
 * que pase.
 */
export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const EMAIL_VACIO_CORPORATIVO =
  "Escribí el email de la empresa: es la casilla a la que el sistema le manda los avisos"

export const EMAIL_MAL_FORMADO =
  "Falta el arroba o el dominio — tiene que ser algo como nombre@empresa.com"

/**
 * `undefined` si el email sirve; si no, el mensaje que dice QUÉ corregir.
 *
 * Los dos mensajes son los de `/empleados`, que ya cumplían la regla del sistema de diseño
 * (§3: el mensaje dice qué corregir, no "el campo es inválido"). Se movieron acá tal cual para
 * que la pantalla piloto no cambie de texto al unificarse.
 *
 * @param valor Lo que el usuario escribió, sin normalizar.
 * @param opts  `vacio`: el mensaje cuando está vacío. Distinto por campo — un email corporativo
 *              y el personal de un candidato no se piden por la misma razón, y el mensaje del
 *              vacío es lo único que puede explicar cuál de los dos es.
 */
export function validarEmail(
  valor: string, opts: { vacio?: string } = {},
): string | undefined {
  const v = valor.trim()
  if (!v) return opts.vacio ?? EMAIL_VACIO_CORPORATIVO
  if (!EMAIL_RE.test(v)) return EMAIL_MAL_FORMADO
  return undefined
}
