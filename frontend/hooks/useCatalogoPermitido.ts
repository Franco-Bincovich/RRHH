"use client"

import { useCanRead } from "@/hooks/useCanWrite"
import type { Seccion } from "@/services/permisos"

/**
 * ¿Este rol puede LEER el catálogo que llena un select? Si no puede, no se lo pide.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * 🔴 QUÉ CIERRA: `mandos_medios` DISPARABA UN 403 POR CADA NAVEGACIÓN.
 * ═══════════════════════════════════════════════════════════════════════════════════
 * El selector de empresa del sidebar pide `GET /api/empresas` al montarse, y ese endpoint está
 * gateado por `Seccion.EMPRESA + READ`, que `mandos_medios` no tiene. O sea: **un 403 en cada
 * carga de página, en el único componente que está en TODAS las pantallas**. El `.catch(() => {})`
 * lo tragaba, así que no rompía nada visible — pero dejaba la consola llena de errores y, sobre
 * todo, enseñaba a ignorar los 403 del log justo en el rol donde importan.
 *
 * Lo mismo, más chico, con `GET /api/areas/opciones` y `GET /api/proyectos`: los piden los
 * filtros de /vacaciones y /ausencias, que son las DOS secciones que `mandos_medios` sí puede
 * ver — y las dos llenan selects con catálogos que ese rol NO puede leer. Cuatro 403 más.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * POR QUÉ NO SE ARREGLA "AMPLIANDO EL PERMISO"
 * ═══════════════════════════════════════════════════════════════════════════════════
 * La salida fácil sería darle a `mandos_medios` lectura sobre áreas, proyectos y empresas para
 * que las llamadas dejen de fallar. Eso es una decisión de PRODUCTO sobre qué ve ese rol, y
 * tomarla de rebote para callar unos 403 la tomaría del peor modo posible: ensanchando el
 * permiso más de lo que nadie pidió. Lo que este hook hace es lo contrario — no pedir lo que ya
 * está decidido que no se puede leer.
 *
 * ⚠️ CONSECUENCIA ASUMIDA, Y HAY QUE DECIRLA: para `mandos_medios` los filtros de área y proyecto
 * de /vacaciones y /ausencias **desaparecen**, y el selector de empresa del sidebar también. No
 * es una pérdida: esos controles ya no funcionaban —el catálogo llegaba vacío por el 403 y el
 * select quedaba con una sola opción— y `limpiarTodoRestituye.test.ts` documenta por qué un campo
 * cuyo catálogo llega vacío es peor que ninguno: el valor sigue vivo en el estado y sigue
 * viajando al backend sin chip que lo quite. 🚩 Disparador para volver sobre esto: que producto
 * decida que ese rol filtra por área.
 *
 * ⚠️ NO ES SEGURIDAD, igual que `useCanWrite`: el backend gatea con 403 de todos modos. Lo que
 * evita es pedir lo que se sabe que va a fallar.
 *
 * 🔑 EL VALOR INICIAL ES `false` MIENTRAS EL ROL NO ESTÁ RESUELTO (`useRol` arranca en null y se
 * hidrata en un efecto). Es el default seguro en la dirección que importa: se pide de más nunca,
 * y en cuanto el rol llega el efecto que depende de esto vuelve a correr. Al revés, el 403 saldría
 * igual en el primer render, que es justo lo que se está cerrando.
 */
export function useCatalogoPermitido(seccion: Seccion): boolean {
  return useCanRead(seccion)
}
