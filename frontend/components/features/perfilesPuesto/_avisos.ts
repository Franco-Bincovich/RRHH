/**
 * Las dos cosas que esta pantalla tiene que DECIR EN VOZ ALTA, y que nadie puede deducir mirándola.
 *
 * Viven como constantes y no escritas en el JSX porque las lee más de un lugar (el encabezado y
 * el estado vacío) y porque son afirmaciones sobre el sistema: si alguna deja de ser cierta, se
 * corrige acá y en ningún otro lado.
 */

/**
 * 🔴 EL SELECTOR DE EMPRESA DEL SIDEBAR NO ACOTA ESTA PANTALLA, y es lo contrario a lo que hace
 * todo el resto del sistema. Ninguna de las 7 rutas de `/api/perfiles-puesto` lee `X-Empresa-Id`:
 * el catálogo es del GRUPO (migración 113), igual que el de clientes. Alguien acostumbrado a que
 * el sidebar filtre va a suponer que está viendo "los perfiles de esta empresa" — y va a crear
 * un duplicado con el mismo nombre para otra sociedad, que es justo lo que el 409 rechaza.
 *
 * Va en el SUBTÍTULO del encabezado y no en un bloque de aviso: describe **lo que la pantalla
 * ES**, no algo que va a pasar. Es la regla que ya está escrita en `AvisoImpacto`.
 */
export const AVISO_CATALOGO_GLOBAL =
  "El catálogo es de todo el grupo: el selector de empresa del sidebar no lo filtra, y el nombre " +
  "de cada perfil tiene que ser único en el sistema entero."

/**
 * 🔴 EL PUENTE PERFIL → VACANTE TODAVÍA NO EXISTE, y hay que decirlo ANTES de que alguien cargue
 * veinte perfiles esperando usarlos.
 *
 * `vacantes.perfil_puesto_id` está en la base, con su FK y su índice, y en **cero schemas
 * Pydantic y cero frontend**: no hay forma de elegir un perfil al crear una vacante. Un perfil
 * cargado hoy no sirve para nada más que verse en esta pantalla y exportarse.
 *
 * Es exactamente la trampa que §7 del sistema de diseño describe —"lo que el equipo ve, lo da
 * por hecho"—, y la única diferencia con las seis cosas que ese capítulo enumera es que ésta SÍ
 * se va a construir. Por eso el texto dice "todavía": no es una promesa rota, es un orden de
 * trabajo, y callarlo haría que la primera vacante se cargue a mano igual que siempre sin que
 * nadie entienda por qué el perfil no aparecía.
 */
export const AVISO_SIN_PUENTE_VACANTE =
  "Los perfiles todavía no se pueden elegir al crear una vacante: el vínculo existe en la base " +
  "pero la pantalla de vacantes todavía no lo usa. Por ahora un perfil sirve para tener el aviso " +
  "escrito en un solo lugar y copiarlo a mano."
