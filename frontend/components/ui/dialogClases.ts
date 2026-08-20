/**
 * Las clases del diálogo: el popup, el cuerpo scrolleable y el patrón de modal de formulario.
 *
 * Viven fuera de `dialog.tsx` porque son la parte del primitivo que se LEE y se DISCUTE —cada
 * una arrastra la explicación de un bug que ya se pagó (el ancho, el scroll, el `dvh`)— y esa
 * prosa hacía crecer el componente sin agregarle una línea de lógica. `dialog.tsx` las
 * re-exporta, así que `import { CLASES_POPUP } from "@/components/ui/dialog"` sigue andando.
 */

/**
 * Las clases del popup y del cuerpo, exportadas para poder testearlas.
 *
 * ⚠️ Están afuera del JSX SOLO por eso: `Dialog` de base-ui monta por PORTAL, y vitest corre sin
 * jsdom, así que `renderToStaticMarkup(<Dialog open>…)` devuelve string VACÍO — no hay forma de
 * afirmar el DOM del diálogo en esta suite. Sacando estas dos constantes, lo que sí queda
 * cubierto es la lógica que puede regresionar (el reparto de hijos) y las clases de las que
 * depende el scroll. Lo que NO queda cubierto es el armado final del JSX; son las 3 líneas de
 * abajo y `partirHijos` garantiza que el footer nunca esté en `cuerpo`, que es lo que haría
 * que se scrollee.
 */
export const CLASES_POPUP =
  // `flex flex-col` reemplaza al `grid` de shadcn: para una sola columna se ven igual, pero flex
  // es lo que permite que el cuerpo ENCOJA (flex-shrink) y los extremos no.
  // `max-h` con `dvh` y NO `vh`: en mobile `vh` cuenta la barra de direcciones aunque esté
  // desplegada, así que el modal queda más alto que lo que se ve. Las 2rem son el aire de 1rem
  // arriba y 1rem abajo.
  /*
   * 🔴 EL ANCHO POR DEFECTO ES `max-w-sm` SIN PREFIJO, Y ESO ES UN ARREGLO, NO UN DETALLE.
   * Hasta el 19/8/2026 esta línea terminaba en **`sm:max-w-sm`**, y eso rompía el ancho de casi
   * todos los modales del repo: `cn()` es `twMerge`, que resuelve el conflicto entre dos clases
   * del MISMO grupo —el `max-w-2xl` del consumidor pisa al `max-w-sm` del primitivo— pero
   * `sm:max-w-sm` y `max-w-2xl` son grupos DISTINTOS (uno lleva variante, el otro no), así que
   * sobrevivían las dos y de 640px para arriba ganaba la del media query. Resultado: un modal que
   * pedía `max-w-4xl` (896px) se veía de **384px**, sin ningún error y sin que el `className` que
   * el autor escribió apareciera tachado en ningún lado. Verificado en el CSS compilado.
   * Lo delataban cinco modales con el workaround local `sm:max-w-lg` / `sm:max-w-md`: alguien lo
   * chocó, lo resolvió en su archivo y el primitivo quedó roto para los otros treinta.
   *
   * El ancho de mobile no se pierde: lo que era `w-full` + `max-w-[calc(100%-2rem)]` ahora es
   * `w-[calc(100%-2rem)]` — el mismo valor, movido de `max-width` a `width` para dejar el
   * `max-width` libre. Un popup `fixed` mide su 100% contra el viewport, así que en un teléfono
   * sigue siendo "todo el ancho menos 1rem de cada lado", y el `max-w-*` del consumidor solo lo
   * puede achicar. Los cinco workarounds se sacaron en el mismo commit: ya no hacen falta.
   */
  "fixed top-1/2 left-1/2 z-50 flex max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-xl bg-popover p-4 text-sm text-popover-foreground ring-1 ring-foreground/10 duration-100 outline-none data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95 " +
  // `shrink-0` a los extremos por SELECTOR y no envolviéndolos en un div: sin él, flex los achica
  // a ellos antes que al cuerpo y el título se aplasta en vez de scrollear la parte larga. Va así
  // para no meter un nodo nuevo entre el popup y el footer — el footer sangra hasta el borde con
  // `-mx-4 -mb-4`, que se miden contra su padre.
  "[&>[data-slot=dialog-footer]]:shrink-0 [&>[data-slot=dialog-header]]:shrink-0"

export const CLASES_CUERPO =
  // `min-h-0` es lo que hace que el scroll ocurra: un hijo flex no baja de su tamaño de contenido
  // sin esto, así que sin él el cuerpo empuja y el modal se desborda igual que antes. `gap-4`
  // repone la separación que daba el contenedor: al envolver los hijos, dejaron de ser hermanos
  // del `gap` de arriba.
  "flex min-h-0 flex-col gap-4 overflow-y-auto"


/**
 * 🔴 EL PATRÓN "MODAL DE FORMULARIO" (`docs/SISTEMA-DE-DISENO.md` §3) — OPT-IN, como el
 * `patron="datos"` de la tabla. Este primitivo lo usan **47 modales**: escribir el vidrio y el
 * ancho de 560px en las clases base los cambiaría a los 47 de una, y la mayoría no son
 * formularios (importadores, fichas, confirmaciones, el visor de un mail). Sin `patron`, un
 * diálogo sale exactamente como salía.
 *
 * Lo que trae, y de dónde sale cada número:
 *
 * · **Vidrio con blur de 28px sobre scrim al 35%.** Es uno de los DOS únicos lugares donde el
 *   sistema de diseño permite vidrio (el otro es el sidebar): "ahí comunica 'esto está adelante'
 *   y hay algo detrás que importa". En una tarjeta de grilla no comunica nada y cuesta
 *   rendimiento, por eso las filas y las tarjetas son opacas.
 *   ⚠️ **El vidrio va bajo `supports-backdrop-filter:`, y el `bg-popover` OPACO queda de base.**
 *   Sin esa guarda, un navegador sin `backdrop-filter` renderiza un fondo al 80% de opacidad sin
 *   nada que lo desenfoque: el texto del modal queda leyéndose encima del listado. La degradación
 *   correcta de "vidrio" no es "traslúcido", es "opaco".
 *
 * · **560px.** El rango del sistema de diseño es 460–560; el tope es el que hay que fijar. Abajo
 *   se lo come el `w-[calc(100%-2rem)]` del popup, que es lo que corresponde en un teléfono.
 *
 * · **Radio de 14px.** No hace falta clase: `rounded-xl` del popup ES 14px —`--radius-xl` es
 *   `calc(var(--radius) * 1.4)` y `--radius` vale 0.625rem—. Está escrito acá porque el número
 *   coincide por derivación y no por casualidad, y alguien que mida 14px y no encuentre un `14`
 *   en el código va a agregarlo dos veces.
 *
 * · **Campos de 34px.** Los `<Select>` ya miden eso con su `size="md"`; los `<Input>` miden 32px
 *   y no tienen variante de tamaño. Se los sube DESDE ACÁ, por descendiente, en vez de tocar
 *   `input.tsx` —que tiene 39 consumidores— o de pedirle una prop nueva a cada campo del
 *   formulario. Abajo de `md` van a 44px, que es el área táctil que el repo usa en todo control.
 *   El campo activo ya lleva `--primary` con anillo de 3px: es el `focus-visible:border-ring
 *   focus-visible:ring-3` que `input.tsx` y `select.tsx` traen de fábrica.
 *
 * · **Mensajes de error de 11px** — los pone cada campo; no se pueden imponer desde acá sin
 *   pisar también el banner de resumen, que es texto distinto y va más grande.
 */
export const PATRON_FORMULARIO = [
  "max-w-[560px]",
  "supports-backdrop-filter:bg-popover/80 supports-backdrop-filter:backdrop-blur-[28px]",
  "[&_[data-slot=input]]:h-11 md:[&_[data-slot=input]]:h-[34px]",
].join(" ")

/**
 * El scrim del patrón de formulario: 35% de negro y **sin blur propio**.
 * El default del diálogo es 10% con un `backdrop-blur-xs`; acá el desenfoque lo pone el popup
 * (28px), y dejar los dos desenfoca el fondo dos veces —una por el scrim y otra por el vidrio—,
 * que se ve turbio y cuesta el doble de composición en cada scroll de fondo.
 */
export const CLASES_SCRIM_FORMULARIO = "bg-black/35 supports-backdrop-filter:backdrop-blur-none"
