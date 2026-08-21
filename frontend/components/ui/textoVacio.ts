import type { ChipFiltro } from "@/components/ui/filtrosChips"

/**
 * El texto del estado VACÍO, armado **con los valores reales de los filtros activos**
 * (`docs/SISTEMA-DE-DISENO.md` §3). El ejemplo del documento es
 * "Bodegas Tupungato no tiene personal de Sistemas suspendido".
 *
 * 🔴 POR QUÉ IMPORTA TANTO COMO PARA TENER SU PROPIO MÓDULO. "No hay resultados" es verdadero y
 * no sirve para nada: el usuario acaba de aplicar cuatro filtros y no sabe **cuál** de los cuatro
 * dejó la tabla en cero. Nombrar los valores convierte la pantalla vacía en la respuesta a la
 * pregunta que la trajo hasta acá, y es lo que hace que la salida obvia —quitar el último
 * filtro— se entienda sin leer instrucciones.
 *
 * 🔴 LOS FILTROS NO SE BORRAN SOLOS. El vacío OFRECE dos salidas y no ejecuta ninguna: si la
 * pantalla se limpiara sola al no encontrar nada, el usuario vería aparecer 31 filas y no
 * entendería que las está mirando sin el filtro que puso.
 *
 * ⚠️ ESTO ES LO ÚNICO DEL PATRÓN QUE NO ES MECÁNICO DE PROPAGAR, y conviene saberlo antes de
 * planificar las otras pantallas: la frase necesita **tres cosas que cada módulo tiene que
 * elegir** —el sustantivo de lo que se lista ("colaboradores", "vacaciones", "ítems"), cuál de
 * sus filtros es el SUJETO de la oración (en empleados, la empresa: "Karstec no tiene…") y el
 * GÉNERO de ese sustantivo—. El resto —enumerar los valores, la coma y la "y" final— sale de los
 * chips sin tocar nada.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 EL GÉNERO ES UN PARÁMETRO PORQUE LA FRASE CONCUERDA EN DOS LUGARES, NO EN UNO.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * Hasta el 21/8/2026 las dos estaban en masculino fijo, y sobre siete de las quince pantallas
 * que usan este helper la frase quedaba mal escrita:
 *
 *   · sin filtros → *"Cuando se cargue **el primero** va a aparecer acá"* → sobre "áreas",
 *     "bajas", "ausencias", "vacantes", "empresas", "vacaciones" y "recategorizaciones".
 *   · con el sujeto como único filtro → *"Karstec no tiene áreas **cargados**"*. Esta segunda es
 *     la que no estaba a la vista y apareció al arreglar la primera: es el MISMO defecto en otra
 *     rama, y se arregla con la misma decisión.
 *
 * Por eso el parámetro es el GÉNERO y no el literal "la primera": una sola decisión por pantalla
 * gobierna las dos concordancias, y no se puede acertar una y errar la otra. Y es una **unión
 * cerrada** (`"masculino" | "femenino"`), no un string libre: un "la primer" o un "los primeros"
 * no compilan.
 *
 * El default es `"masculino"`, así que las ocho pantallas que ya estaban bien no cambian ni una
 * línea — y ese default es también lo que hace que el cambio sea imposible de romper por omisión.
 */

/** Une con comas y una "y" antes del último: "A, B y C". Un listado con "A, B, C" se lee como
 *  una enumeración inconclusa. */
function enumerar(partes: string[]): string {
  if (partes.length <= 1) return partes[0] ?? ""
  return `${partes.slice(0, -1).join(", ")} y ${partes[partes.length - 1]}`
}

export interface TextoVacio {
  titulo: string
  descripcion: string
}

/** El género del sustantivo que se lista. Ver el 🔴 del encabezado: gobierna las DOS
 *  concordancias de la frase, no una. */
export type GeneroSustantivo = "masculino" | "femenino"

/**
 * @param chips       los filtros activos, ya derivados (mismo origen que la fila de chips)
 * @param sustantivo  qué se está listando, en plural: "colaboradores"
 * @param claveSujeto qué chip actúa de sujeto de la oración, si está puesto: "Empresa"
 * @param genero      el del sustantivo. Default "masculino": las pantallas que ya concordaban
 *                    no cambian.
 */
export function textoVacio(
  chips: ChipFiltro[], sustantivo: string, claveSujeto?: string,
  genero: GeneroSustantivo = "masculino",
): TextoVacio {
  const femenino = genero === "femenino"

  // Sin filtros no es "no encontré": es que todavía no hay nada cargado. Son dos pantallas
  // distintas y confundirlas manda al usuario a revisar filtros que no puso.
  if (chips.length === 0) {
    return {
      titulo: `Todavía no hay ${sustantivo}`,
      descripcion: `Cuando se cargue ${femenino ? "la primera" : "el primero"} va a aparecer acá.`,
    }
  }

  const sujeto = claveSujeto ? chips.find((c) => c.clave === claveSujeto) : undefined
  const resto = chips.filter((c) => c !== sujeto)
  const condiciones = enumerar(resto.map((c) => `${c.etiqueta.toLowerCase()} ${c.valor}`))

  if (sujeto && condiciones) {
    return {
      titulo: "Ningún resultado con estos filtros",
      descripcion: `${sujeto.valor} no tiene ${sustantivo} con ${condiciones}.`,
    }
  }
  if (sujeto) {
    return {
      titulo: "Ningún resultado con estos filtros",
      descripcion: `${sujeto.valor} no tiene ${sustantivo} ${femenino ? "cargadas" : "cargados"}.`,
    }
  }
  return {
    titulo: "Ningún resultado con estos filtros",
    descripcion: `No hay ${sustantivo} con ${condiciones}.`,
  }
}
