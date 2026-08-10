import type { Hora } from "@/types/proyecto"

const MODALIDAD: Record<string, string> = { home_office: "Home Office", on_site: "On site" }

/**
 * Las dos decisiones de presentación del detalle día por día, sueltas y puras.
 *
 * Viven fuera del modal a propósito: `DetalleEmpleadoModal` usa `Dialog` de Radix, que monta por
 * PORTAL, y con vitest SIN jsdom `renderToStaticMarkup` devuelve "". Un test del componente
 * pasaría con el contenido entero borrado, así que lo que se prueba es esto.
 */

/**
 * dd/mm de una fecha ISO (`YYYY-MM-DD`).
 *
 * 🔴 NO pasa por `new Date` NI por `toLocaleDateString`, y las dos omisiones tienen motivo:
 *   · `new Date("2026-08-10")` se interpreta en UTC, así que en Argentina (UTC-3) muestra el 09.
 *     Se puede evitar con `T00:00:00`, pero entonces queda la segunda.
 *   · `toLocaleDateString("es-AR", { month: "2-digit" })` NO paddea en un Node sin ICU completo:
 *     devuelve "10/8" en vez de "10/08". Lo encontró el test, no la lectura.
 * Cortar el string es determinístico, no depende del entorno y no tiene zona horaria.
 */
export function formatFechaCorta(iso: string): string {
  const [, mm, dd] = iso.split("-")
  return `${dd}/${mm}`
}

/**
 * La línea descriptiva de una carga: cliente · proyecto · tarea · modalidad, sin los vacíos.
 *
 * 🔴 "Sin cliente" se escribe explícito y no se deja en blanco: una carga del camino viejo NO
 * tiene cliente por diseño, y un hueco se lee como un dato que falta. Y si no queda NADA que
 * decir, devuelve "Sin detalle" en vez de "" — un renglón que muestra solo la fecha y las horas
 * parece cortado a la mitad.
 */
export function textoDeCarga(h: Hora): string {
  const partes = [
    h.cliente_nombre ?? "Sin cliente",
    h.proyecto_texto,
    h.tarea_texto,
    h.modalidad ? MODALIDAD[h.modalidad] : null,
  ].filter(Boolean)
  return partes.length ? partes.join(" · ") : "Sin detalle"
}
