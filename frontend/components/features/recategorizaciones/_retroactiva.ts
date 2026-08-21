import type { Recategorizacion } from "@/types/recategorizacion"

/**
 * La regla que el usuario NO puede deducir mirando el formulario, y que tiene que ver ANTES de
 * apretar Guardar.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 EL LEGAJO SOLO SE PISA SI LA FILA ES LA MÁS RECIENTE.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * `_recategorizaciones_write` aplica el cambio al colaborador **solo si** la `fecha_efectiva` que
 * se está cargando es posterior a la de la última recategorización existente de esa persona.
 * O sea: cargar una del 1/8 cuando ya hay una del 1/9 **registra el histórico y NO cambia el
 * legajo actual** — que es lo correcto (el rol vigente lo fijó el cambio de septiembre), y es
 * exactamente lo que nadie adivina desde el formulario.
 *
 * Sin este aviso, el modo de falla es mudo: se carga la recategorización retroactiva, la pantalla
 * responde 201, la fila aparece en la planilla… y el rol del colaborador sigue siendo el de
 * antes. La lectura razonable es "el sistema no aplicó el cambio", y el paso siguiente es
 * cargarla de nuevo o editar el legajo a mano, que es justo lo que rompe la cadena.
 *
 * ⚠️ ES UN AVISO DE IMPACTO, no una validación: la operación es LEGÍTIMA y se guarda igual. Por
 * eso va en ámbar sobre el pie del modal (`AvisoImpacto`) y no como error de campo en rojo — dice
 * "esto va a pasar", no "esto está mal". Es literalmente el caso de uso que `AvisoImpacto`
 * documenta.
 */

/** La fecha de la última recategorización de esa persona, o `null` si nunca tuvo. */
export function ultimaFechaEfectiva(historial: Recategorizacion[]): string | null {
  // El backend devuelve el historial de más reciente a más viejo, pero no se confía en el orden
  // para una decisión que cambia lo que la pantalla afirma: se toma el máximo. Las fechas son
  // ISO `YYYY-MM-DD`, así que comparar como texto es comparar cronológicamente.
  return historial.reduce<string | null>(
    (max, r) => (max === null || r.fecha_efectiva > max ? r.fecha_efectiva : max),
    null,
  )
}

/**
 * ¿La fecha elegida deja esta recategorización FUERA de la punta de la cadena?
 *
 * `true` = se registra el histórico pero el legajo no se toca. Los tres casos que devuelven
 * `false` importan y son distintos entre sí:
 *   · no hay ninguna previa (`ultima === null`) → esta ES la más reciente;
 *   · la fecha elegida es posterior → es la nueva punta;
 *   · **la fecha elegida es IGUAL a la última** → el backend la trata como la más reciente y sí
 *     pisa el legajo, así que avisar acá sería mentir.
 */
export function avisoRetroactivo(fechaElegida: string, ultima: string | null): boolean {
  if (!fechaElegida || ultima === null) return false
  return fechaElegida < ultima
}

/** El texto del aviso. Constante para que el modal y su test digan exactamente lo mismo. */
export const TEXTO_AVISO_RETROACTIVO =
  "Esta fecha es anterior a la última recategorización de esta persona, así que se va a registrar " +
  "en el histórico pero NO va a cambiar el rol, la seniority ni la categoría del legajo: esos " +
  "los fija la recategorización más reciente."
