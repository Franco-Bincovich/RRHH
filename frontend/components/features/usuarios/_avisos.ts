/**
 * Las dos cosas que este módulo tiene que DECIR EN VOZ ALTA, y que nadie puede deducir mirando la
 * pantalla. Molde: `perfilesPuesto/_avisos.ts`.
 *
 * ⚠️ El archivo se llama `_avisos.ts` en plural —y en clientes y empresas el equivalente se llama
 * `_avisoGlobal.ts`, en singular— porque acá hay DOS: el alcance de un usuario y la contraseña
 * que se muestra una sola vez. El nombre sigue al contenido, no al revés.
 */

/**
 * 🔴 EL SELECTOR DE EMPRESA DEL SIDEBAR NO ACOTA ESTA PANTALLA, y no por un descuido de
 * implementación sino por una decisión de producto que este repo ya tiene cerrada: **los usuarios
 * NO cuelgan de una empresa**. `GET /api/usuarios` no lee `X-Empresa-Id` ni acepta ningún Query,
 * y `DELETE /{user_id}` está declarado NO APLICA en el barrido de la barrera de empresa (Fase 2)
 * con esa misma razón escrita.
 *
 * El corolario que hay que decir en voz alta, porque es lo que un operador no puede deducir
 * mirando la tabla: **todo usuario, sin importar su rol, accede a TODAS las empresas**. No existe
 * "usuario limitado a ciertas empresas". Quien crea un acceso acá lo está creando para el grupo
 * entero.
 *
 * Va en el SUBTÍTULO del encabezado y no en un bloque de aviso: describe **lo que la pantalla
 * ES**, no algo que va a pasar. Misma regla y mismo lugar que en clientes y empresas.
 */
export const AVISO_CATALOGO_GLOBAL =
  "los usuarios no pertenecen a una empresa: el selector del sidebar no filtra esta pantalla y " +
  "cada acceso alcanza a todas las empresas del grupo."

/**
 * 🔴 LA CONTRASEÑA TEMPORAL SE MUESTRA UNA SOLA VEZ, y es la consecuencia que más se olvida de
 * este formulario: al confirmar, el backend la genera y la devuelve en esa única respuesta —no se
 * guarda en claro, así que no hay pantalla ni endpoint que la pueda volver a mostrar—. Quien
 * cierra el modal sin copiarla tiene que dar de baja el usuario y crearlo de nuevo.
 *
 * Va en la `DialogDescription` del modal: es exactamente el lugar que el patrón reserva para "lo
 * que va a pasar cuando aprietes Guardar" (§3), y lo que el usuario no puede deducir de los
 * campos que está completando.
 */
export const AVISO_PASSWORD_UNICA =
  "Se crea el acceso y se muestra una contraseña temporal una sola vez: copiala antes de cerrar. " +
  "La persona la cambia en su primer ingreso."
