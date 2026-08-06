/**
 * Cómo se LEE el contrato de una asignación a proyecto (valor hora y período).
 *
 * Módulo aparte y no funciones dentro de CardsProyecto porque aquel quedaba sobre su límite de
 * 150 al sumarlas, y porque siendo puras se testean directo, sin renderizar nada.
 *
 * 🔴 LA REGLA DE FONDO: un `valor_hora` de 0 NO es "cobra cero", es "no está cargado", y una
 * fecha nula no es "sin límite", es "no se definió". Hoy las 31 asignaciones de producción
 * están así: valor_hora 0 y las dos fechas en null, o sea el 100% de las filas. Mostrar "$0"
 * afirmaría un acuerdo económico que nadie pactó, y sobre una card de organigrama —que se mira
 * de reojo— esa afirmación se toma por buena. Por eso el importe solo se muestra cuando es > 0.
 */

const ARS = new Intl.NumberFormat("es-AR", {
  style: "currency",
  currency: "ARS",
  maximumFractionDigits: 0,
})

export const SIN_DEFINIR = "Sin definir"

/**
 * "2026-03-01" → "01/03/2026", partiendo el string.
 *
 * 🔴 NO se usa `new Date(iso)`: un ISO de SOLO FECHA se parsea como UTC y en Argentina (UTC−3)
 * `toLocaleDateString` devuelve el DÍA ANTERIOR. `fecha_desde`/`fecha_hasta` son columnas
 * `date`, así que caen justo en ese caso. Mismo molde que `SaldoResumen` y `VacacionesTable`,
 * que ya documentan el mismo problema.
 */
function fecha(iso: string): string {
  const [a, m, d] = iso.slice(0, 10).split("-")
  return d ? `${d}/${m}/${a}` : iso
}

/** El valor hora como moneda, o "Sin definir" si es 0, null o algo que no es un número. */
export function valorHoraTexto(valor: number | null | undefined): string {
  if (typeof valor !== "number" || !Number.isFinite(valor) || valor <= 0) return SIN_DEFINIR
  return `${ARS.format(valor)}/h`
}

/**
 * El período de la asignación, con lo que haya:
 *   las dos    → "01/03/2026 – 30/06/2026"
 *   solo desde → "Desde 01/03/2026"      (sigue vigente, sin fin pactado)
 *   solo hasta → "Hasta 30/06/2026"
 *   ninguna    → "Sin definir"
 *
 * Las cuatro ramas existen porque las dos columnas son independientes en la base: nada obliga a
 * cargar una para cargar la otra. Colapsar los casos de una sola fecha en "Sin definir" tiraría
 * el único dato que sí se cargó.
 */
export function periodoTexto(desde: string | null, hasta: string | null): string {
  if (desde && hasta) return `${fecha(desde)} – ${fecha(hasta)}`
  if (desde) return `Desde ${fecha(desde)}`
  if (hasta) return `Hasta ${fecha(hasta)}`
  return SIN_DEFINIR
}
