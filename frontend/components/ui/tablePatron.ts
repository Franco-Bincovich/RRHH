/**
 * La definición del patrón "Tabla con paginación" de `docs/SISTEMA-DE-DISENO.md` §3, en clases.
 * Vive aparte de `table.tsx` para que el primitivo quede adentro del límite de 150 sin recortar
 * la explicación de por qué el patrón es opt-in — que es lo único que impide que la próxima
 * sesión lo "simplifique" a las clases base y migre 31 pantallas sin querer.
 */
/**
 * 🔴 `patron="datos"` ES OPT-IN, Y ESO ES EL ALCANCE, NO UNA DUDA.
 * Este primitivo tiene **31 consumidores**. Escribir el patrón de tabla de
 * `docs/SISTEMA-DE-DISENO.md` §3 en las clases base habría cambiado de golpe la densidad, el
 * encabezado y el hover de 31 pantallas, incluidas las que no son listados paginados (tablas de
 * dos filas dentro de un modal, resúmenes de import, la grilla de resultados de evaluaciones).
 * Con la variante, una tabla que no la pide sale exactamente igual que antes: `patron` undefined
 * no agrega una sola clase.
 *
 * Lo que agrega `patron="datos"`, todo desde acá y sin tocar el consumidor:
 *   · filas de 46px (densidad alta: "un sistema de gestión no es una landing")
 *   · encabezado de 32px en la superficie secundaria, mayúsculas de 10px
 *   · separadores de 1px — ya estaban, es el `border-b` de `TableRow`
 *   · hover: fondo tenue + marca de 3px de `--primary` a la izquierda + 2px de desplazamiento,
 *     en 160ms, **sin elevación** (en una tabla la elevación rompe la alineación de las columnas)
 *
 * ⚠️ Las clases se escriben como variantes arbitrarias sobre descendientes (`[&_tbody_tr]:...`)
 * y no como props en `TableRow`/`TableHead`. El motivo es que el consumidor NO tenga que repetir
 * nada fila por fila: si el patrón viviera en props, aplicarlo sería tocar cada `<TableRow>` de
 * cada pantalla y la primera que se olvide de una queda con dos densidades en la misma tabla.
 */

/** La marca de hover es un `box-shadow` INTERIOR: dibuja los 3px adentro de la fila, así no
 *  empuja las columnas ni suma ancho — un `border-left` real correría todo el contenido. */
export const PATRON_DATOS = [
  "[&_thead_th]:h-8 [&_thead_th]:bg-secondary [&_thead_th]:text-[10px] [&_thead_th]:font-semibold",
  "[&_thead_th]:uppercase [&_thead_th]:tracking-wider [&_thead_th]:text-muted-foreground",
  "[&_tbody_tr]:h-[46px] [&_tbody_tr]:transition-[transform,box-shadow,background-color]",
  "[&_tbody_tr]:duration-[160ms] [&_tbody_tr]:shadow-[inset_3px_0_0_0_transparent]",
  /*
   * `:not([data-vacio])` — la fila del estado VACÍO no es una fila de datos: es el panel entero
   * ocupando un `colSpan`. Sin la exclusión, pasar el mouse por el bloque que explica que no hay
   * resultados lo desplaza 2px y le dibuja la marca de selección al costado, como si fuera un
   * registro que se puede abrir. La especificidad del selector del patrón (`.clase tbody tr:hover`)
   * le gana a cualquier `hover:translate-x-0` que la fila declare, así que la excepción tiene que
   * vivir acá y no en el consumidor.
   */
  "[&_tbody_tr:not([data-vacio]):hover]:translate-x-[2px]",
  "[&_tbody_tr:not([data-vacio]):hover]:shadow-[inset_3px_0_0_0_var(--primary)]",
].join(" ")

