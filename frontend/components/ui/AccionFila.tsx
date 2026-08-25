import type { ButtonHTMLAttributes } from "react"

import { cn } from "@/lib/utils"

/**
 * La CAJA de una acción de fila, como clase suelta.
 *
 * 🔑 EXISTE PARA LOS `<Link>`, que no pueden ser un `<button>` y sí tienen que medir lo mismo. El
 * caso real es la flecha "Ver la ficha" de /empresas: es navegación, así que tiene que ser un
 * ancla de verdad —abrible en pestaña nueva, alcanzable por teclado— y a la vez uno de los
 * controles de 32px que esta tanda subió a 44 abajo de `md`. Exportar la clase es lo que evita
 * que ese caso vuelva a copiar el estilo a mano, que es de donde salieron las 9 copias de
 * `ACCION_CLASS`.
 */
/**
 * EL PISO TÁCTIL, como clase suelta, para los controles que NO son ni un `<Button>` ni una acción
 * de fila y por lo tanto tienen su caja escrita a mano.
 *
 * 🔴 CUÁNDO SE USA, Y CUÁNDO NO. No es una alternativa a los primitivos: si el control es un botón
 * del producto, va `<Button>`; si es la acción de una fila, va `<AccionFila>`. Esto es para los
 * pocos que son OTRA cosa —el nodo de un árbol, una fila de un combobox, un toggle de semana del
 * onboarding— y cuya caja la decide su contexto. Medidos el 25/8/2026: **11 botones en 8
 * archivos**, y `barridoTouchTarget.test.ts` no deja que aparezca un doceavo sin piso.
 *
 * 🔑 `md:min-h-0` DEVUELVE EL DESKTOP EXACTAMENTE COMO ESTABA. El piso sólo rige abajo de `md`,
 * que es donde se toca con el dedo; arriba, el alto vuelve a ser el que el control ya tenía. Por
 * eso se puede agregar sin revisar el diseño de cada uno.
 */
export const PISO_TACTIL = "min-h-11 md:min-h-0"

/** El piso táctil de un control de sólo ícono: hace falta el ANCHO además del alto. */
export const PISO_TACTIL_ICONO = "min-h-11 min-w-11 md:min-h-0 md:min-w-0"

export const claseAccionFila = cn(
  "flex size-11 shrink-0 items-center justify-center rounded-md md:size-8",
  "text-muted-foreground transition-colors group-hover:text-primary hover:bg-accent",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
)

/**
 * La acción de una FILA de tabla o de una tarjeta: un ícono (o un texto corto) que ejecuta algo
 * sobre ese registro.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * 🔴 QUÉ CIERRA: **97 CONTROLES POR DEBAJO DEL MÍNIMO TÁCTIL, EN 8 PANTALLAS.**
 * ═══════════════════════════════════════════════════════════════════════════════════
 * Los botones de encabezado ya median 44px —cada uno con su `min-h-11` escrito a mano— y los de
 * FILA median 32; "Ver detalle" de /auditoria median **24**. Esos son justamente los que más se
 * aprietan: editar, borrar, ver el historial, abrir el detalle.
 *
 * Y no era un descuido puntual: la clase estaba **copiada literal en 9 archivos** como
 * `const ACCION_CLASS`, con dos variantes (una con `disabled:` y otra sin). Es exactamente el
 * modo de falla de los 81 `<select>` con 29 constantes de estilo copiadas, y de los 44 mensajes
 * de error por campo con tres tamaños distintos: cuando el estilo vive en el consumidor, el
 * primer arreglo llega a uno solo.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * LA REGLA, QUE ES LA MISMA QUE LA DE `select.tsx` Y `button.tsx`
 * ═══════════════════════════════════════════════════════════════════════════════════
 * **44px hasta `md`, el tamaño del diseño de `md` para arriba** (`size-11 md:size-8`). El corte es
 * por ancho de pantalla y no por dispositivo: abajo de `md` es donde se usa con el dedo. Arriba de
 * `md` la caja vuelve a 32px, así que **la densidad de la fila no cambia** — que es la otra mitad
 * del requisito: una tabla de 46px de alto sigue midiendo 46px.
 *
 * 🔑 POR QUÉ NO ES UNA VARIANTE MÁS DE `<Button>`. Este control es visualmente distinto a
 * propósito y esa diferencia está decidida en §3: **está siempre visible y sólo cambia de COLOR
 * al apuntar**, sin fondo ni borde en reposo. Un `<Button variant="ghost" size="icon">` trae el
 * `hover:bg-muted` y el `active:translate-y-px` del sistema de botones, que en una grilla de
 * cinco acciones por fila es ruido. Lo que sí comparte es la regla de tamaño, y por eso las dos
 * viven escritas con la misma forma.
 *
 * ⚠️ `tono="destructivo"` NO pinta de rojo en reposo. El rojo aparece con el mouse en la fila
 * (`group-hover:text-destructive`), y es una decisión escrita: una columna de tachos rojos en
 * reposo se lee como una lista de errores, cuando cada fila es un dato sano. El `group` lo pone
 * la `<TableRow>`.
 */
export function AccionFila({
  tono = "normal",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  /** `destructivo` vira a rojo al apuntar la fila, nunca en reposo — ver arriba. */
  tono?: "normal" | "destructivo"
}) {
  return (
    <button
      type="button"
      data-slot="accion-fila"
      className={cn(
        // 44px de lado abajo de `md`; 32px (el tamaño del diseño) de `md` para arriba.
        "flex size-11 shrink-0 items-center justify-center rounded-md md:size-8",
        "text-muted-foreground transition-colors hover:bg-accent",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        "disabled:pointer-events-none disabled:opacity-50",
        tono === "destructivo" ? "group-hover:text-destructive" : "group-hover:text-primary",
        className,
      )}
      {...props}
    />
  )
}

/**
 * La misma acción de fila, pero con TEXTO en vez de ícono ("Ver detalle").
 *
 * Alto fijo de 44px abajo de `md` y `auto` arriba: el ancho lo pone el texto, así que sólo hay que
 * garantizar la altura. Nació con un consumidor —el "Ver detalle" de /auditoria, que median 24px,
 * el control más chico del producto— y se separa de `AccionFila` porque aquélla es cuadrada
 * (`size-*` fija ancho y alto) y ésta no puede serlo.
 */
export function AccionFilaTexto({
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      data-slot="accion-fila"
      className={cn(
        "flex h-11 shrink-0 items-center rounded-md px-2 text-xs md:h-7",
        "text-muted-foreground transition-colors group-hover:text-primary hover:bg-accent",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        "disabled:pointer-events-none disabled:opacity-50",
        className,
      )}
      {...props}
    />
  )
}
