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
 * planificar las otras pantallas: la frase necesita **dos palabras que cada módulo tiene que
 * elegir** —el sustantivo de lo que se lista ("colaboradores", "vacaciones", "ítems") y cuál de
 * sus filtros es el SUJETO de la oración (en empleados, la empresa: "Karstec no tiene…")—.
 * El resto —enumerar los valores, la coma y la "y" final— sale de los chips sin tocar nada.
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

/**
 * @param chips       los filtros activos, ya derivados (mismo origen que la fila de chips)
 * @param sustantivo  qué se está listando, en plural: "colaboradores"
 * @param claveSujeto qué chip actúa de sujeto de la oración, si está puesto: "Empresa"
 */
export function textoVacio(chips: ChipFiltro[], sustantivo: string, claveSujeto?: string): TextoVacio {
  // Sin filtros no es "no encontré": es que todavía no hay nada cargado. Son dos pantallas
  // distintas y confundirlas manda al usuario a revisar filtros que no puso.
  if (chips.length === 0) {
    return {
      titulo: `Todavía no hay ${sustantivo}`,
      descripcion: `Cuando se cargue el primero va a aparecer acá.`,
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
      descripcion: `${sujeto.valor} no tiene ${sustantivo} cargados.`,
    }
  }
  return {
    titulo: "Ningún resultado con estos filtros",
    descripcion: `No hay ${sustantivo} con ${condiciones}.`,
  }
}
