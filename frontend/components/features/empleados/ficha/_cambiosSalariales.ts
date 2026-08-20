import type { EntradaHistorial } from "@/components/ui/Historial"
import type { HistorialSalarialItem } from "@/types/costo"

const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

export function pesos(n: number): string {
  const abs = Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".")
  return n < 0 ? `-$${abs}` : `$${abs}`
}

/**
 * La serie de sueldos → la lista de CAMBIOS que el patrón de historial dibuja.
 *
 * 🔴 LA SERIE NO ES EL HISTORIAL, aunque el historial salga de ella. `costos_nomina` guarda una
 * fila por empleado por mes (UNIQUE empleado_id, anio, mes), así que con dos años cargados hay 24
 * renglones de los cuales 21 dicen exactamente lo mismo que el anterior. Lo que Capital Humano
 * mira en una ficha no es "cuánto cobró cada mes" —para eso está el módulo de costos— sino
 * **cuándo le cambió el sueldo y de cuánto a cuánto**.
 *
 * 🔴 NADA SE OCULTA EN SILENCIO: los meses sin cambio se colapsan, pero la pantalla dice cuántos
 * períodos hay cargados en total (`resumen`). Un colapso mudo se lee como datos faltantes.
 *
 * ⚠️ Compara el BRUTO, y el neto va como detalle. Son dos series distintas y el bruto es el que
 * define el cambio: el neto se mueve solo por retenciones sin que nadie haya tocado el sueldo, y
 * usarlo como disparador marcaría aumentos que no existieron.
 *
 * Recibe la serie tal como la devuelve el backend (más reciente primero) y la devuelve igual.
 */
export function cambiosSalariales(serie: HistorialSalarialItem[]): EntradaHistorial[] {
  const entradas: EntradaHistorial[] = []
  serie.forEach((item, i) => {
    // El siguiente en la lista es el mes ANTERIOR en el tiempo: la serie viene descendente.
    const previo = serie[i + 1]
    if (previo && previo.monto_bruto === item.monto_bruto) return
    entradas.push({
      clave: `${item.anio}-${item.mes}`,
      fecha: `${MESES[item.mes - 1]} ${item.anio}`,
      desde: previo ? pesos(previo.monto_bruto) : null,
      hasta: pesos(item.monto_bruto),
      detalle: `neto ${pesos(item.monto_neto)}`,
    })
  })
  return entradas
}

/** La línea que hace explícito el colapso. Vacía cuando no hay nada que aclarar. */
export function resumenSerie(serie: HistorialSalarialItem[], cambios: number): string {
  if (serie.length === 0) return ""
  const periodos = `${serie.length} ${serie.length === 1 ? "período cargado" : "períodos cargados"}`
  return cambios === serie.length ? periodos : `${periodos} · ${cambios} con cambio de bruto`
}
