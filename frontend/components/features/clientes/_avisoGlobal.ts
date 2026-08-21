/**
 * 🔴 EL SELECTOR DE EMPRESA DEL SIDEBAR NO ACOTA ESTA PANTALLA, y es lo contrario a lo que hace
 * todo el resto del sistema.
 *
 * Ninguna ruta de `/api/clientes` lee `X-Empresa-Id` ni acepta un `empresa_id`: el catálogo es
 * del GRUPO desde las migraciones 108/109, que quitaron la columna `clientes.empresa_id` y
 * pusieron el índice único de nombre a nivel de TODO el sistema (`ux_clientes_nombre_global`,
 * case-insensitive). Alguien acostumbrado a que el sidebar filtre va a suponer que está viendo
 * "los clientes de esta empresa" — y va a crear un duplicado para otra sociedad, que es justo lo
 * que ese índice rechaza con un 409.
 *
 * Va en el SUBTÍTULO del encabezado y no en un bloque de aviso: describe **lo que la pantalla
 * ES**, no algo que va a pasar. Misma regla y mismo lugar que `AVISO_CATALOGO_GLOBAL` de
 * perfiles de puesto, el otro catálogo del grupo.
 *
 * Vive como constante y no escrito en el JSX porque es una afirmación sobre el sistema: si deja
 * de ser cierta, se corrige acá y en ningún otro lado.
 */
export const AVISO_CATALOGO_GLOBAL =
  "el catálogo es de todo el grupo: el selector de empresa del sidebar no lo filtra, y el nombre " +
  "de cada cliente tiene que ser único en el sistema entero."
