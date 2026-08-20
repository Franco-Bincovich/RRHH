import type { FiltroCampo } from "@/components/ui/filtrosTipos"

/**
 * Derivación de los CHIPS de la fila inferior del panel de filtros
 * (`docs/SISTEMA-DE-DISENO.md` §3): "un chip por filtro con su valor y una ✕ para quitarlo".
 *
 * Es una función pura sobre los `FiltroCampo` que la pantalla ya le pasa a `<FiltersBar>`, y esa
 * es la decisión importante de todo el patrón:
 *
 * 🔴 EL CHIP MUESTRA EL LABEL LEGIBLE, Y NO HAY FORMA DE QUE UNA PANTALLA LO HAGA MAL.
 * Un chip que diga `estado: preingreso` está mal; tiene que decir `Estado: Preingreso`. El label
 * NO se pide como dato nuevo: sale de las MISMAS `opciones` que llenan el `<select>`
 * (`{ value: "preingreso", label: "Preingreso" }`). O sea, el texto del chip y el texto de la
 * opción elegida son literalmente el mismo string, y no pueden divergir.
 * La alternativa —que cada pantalla pase un mapa `value → label` para los chips— es la que se
 * puede hacer mal, y se haría mal en 37 pantallas: dos catálogos del mismo dato, uno de los cuales
 * solo se mira cuando hay un chip puesto, así que un valor nuevo sin traducir se ve recién en
 * producción. Acá un valor nuevo se traduce solo, porque ya tuvo que traducirse para el select.
 *
 * ⚠️ Si el valor NO está en `opciones` —los catálogos (áreas, proyectos) llegan por fetch y el
 * filtro puede venir sembrado desde la querystring antes de que lleguen— el chip muestra el valor
 * crudo en vez de desaparecer. Es feo por un instante y es a propósito: un filtro activo INVISIBLE
 * es la pantalla mostrando 4 filas de 31 sin decir por qué.
 */

export type ChipFiltro = {
  /** Clave estable para React. Es el `label` del campo: no hay dos campos con el mismo. */
  clave: string
  /** El nombre del filtro, legible: "Estado". */
  etiqueta: string
  /** El valor elegido, legible: "Preingreso". */
  valor: string
  /**
   * Quita el filtro. 🔴 Llama al MISMO `onChange` que el control, con el valor vacío — no toca el
   * estado de la pantalla por otro camino. Por eso quitar un chip hereda gratis todo lo que la
   * pantalla cuelga de ese onChange: el reseteo a página 1 (invariante 4 del bloque B) y los
   * efectos propios de cada filtro, como el de Empresa en empleados, que además limpia el Área
   * (un área de otra empresa dejaría el listado en cero sin explicación).
   */
  quitar: () => void
}

/** "2026-03-25" → "25/03/2026". Sin `new Date`: parsear un ISO suelto corre la fecha un día
 *  para atrás en cualquier huso al oeste de UTC, y acá se muestra tal cual la eligió el usuario. */
function fechaLegible(iso: string): string {
  const [anio, mes, dia] = iso.split("-")
  return dia && mes && anio ? `${dia}/${mes}/${anio}` : iso
}

/** El label de un valor dentro de las opciones del propio control. Ver el 🔴 del encabezado. */
function labelDe(opciones: { value: string; label: string }[], value: string): string {
  return opciones.find((o) => o.value === value)?.label ?? value
}

/**
 * Un chip por campo con valor. Un campo sin valor no produce chip, así que
 * `chipsDeCampos(campos).length` ES el contador de "N filtros activos" de la fila inferior.
 *
 * ⚠️ El `multiselect` produce UN chip con sus valores juntos ("Áreas: Sistemas, Ventas") y su ✕
 * los quita todos, en vez de un chip por valor. Es lo que dice el sistema de diseño ("un chip por
 * filtro") y lo que hace que el contador y la cantidad de chips sean el mismo número — con un chip
 * por valor, "2 filtros activos" arriba de tres chips se lee como un error. Si algún módulo llega
 * a tener un multiselect de muchas opciones donde quitar de a una importe, ESO es lo que hay que
 * discutir de nuevo; hoy ninguno lo tiene.
 */
export function chipsDeCampos(campos: FiltroCampo[]): ChipFiltro[] {
  const chips: ChipFiltro[] = []
  for (const campo of campos) {
    const base = { clave: campo.label, etiqueta: campo.label }
    switch (campo.tipo) {
      case "select":
        if (campo.value) chips.push({ ...base, valor: labelDe(campo.opciones, campo.value), quitar: () => campo.onChange("") })
        break
      case "search":
        // `.trim()`: un buscador con espacios no filtra nada y un chip vacío no se puede quitar
        // porque no dice qué está filtrando.
        if (campo.value.trim()) chips.push({ ...base, valor: campo.value.trim(), quitar: () => campo.onChange("") })
        break
      case "date":
        if (campo.value) chips.push({ ...base, valor: fechaLegible(campo.value), quitar: () => campo.onChange("") })
        break
      case "daterange": {
        const { desde, hasta } = campo.value
        // Los rangos abiertos son válidos y se leen distinto: "desde el 1/3" no es "1/3 – ".
        const valor = desde && hasta ? `${fechaLegible(desde)} – ${fechaLegible(hasta)}`
          : desde ? `desde ${fechaLegible(desde)}` : hasta ? `hasta ${fechaLegible(hasta)}` : ""
        if (valor) chips.push({ ...base, valor, quitar: () => campo.onChange({ desde: "", hasta: "" }) })
        break
      }
      case "multiselect":
        if (campo.value.length > 0) {
          chips.push({
            ...base,
            valor: campo.value.map((v) => labelDe(campo.opciones, v)).join(", "),
            quitar: () => campo.onChange([]),
          })
        }
        break
    }
  }
  return chips
}
