import type { Empleado } from "@/types/empleado"

import { hoyISO } from "../modal/form-utils"

/**
 * Los CUATRO datos clave de la barra de identidad (`docs/SISTEMA-DE-DISENO.md` §3).
 *
 * 🔴 POR QUÉ ESTOS CUATRO, entre los ~30 campos que la ficha muestra. La barra de identidad
 * contesta una sola pregunta —**quién es esta persona dentro de la organización**— y cada uno
 * de los cuatro contesta una parte que las otras no:
 *
 *   · **Empresa** — de qué sociedad cobra. Es multiempresa: sin esto, dos legajos idénticos de
 *     dos sociedades distintas se leen igual, y es el primer filtro que usa Capital Humano.
 *   · **Área** — dónde trabaja. El eje por el que se corta casi todo reporte.
 *   · **Superior** — a quién responde. Es `manager_id`, que además es el eje de ownership de
 *     `mandos_medios`: quién ve esta ficha depende de este campo.
 *   · **Ingreso** — desde cuándo. Se muestra como ANTIGÜEDAD y no como fecha cruda: "3 años" es
 *     lo que alguien necesita saber de un vistazo; la fecha exacta está en el panel laboral.
 *
 * Qué quedó afuera y por qué, para no rediscutirlo:
 *   · **Rol / puesto** — es el candidato más obvio, y no entra porque ya está EN LA LÍNEA DE
 *     ABAJO DEL NOMBRE (era el subtítulo de la ficha y se conserva). Gastar uno de los cuatro en
 *     repetirlo es perder un cuarto de la barra.
 *   · **Legajo, documento** — son identificadores para buscar, no para entender; van en el panel.
 *   · **Modalidad, seniority, turno** — son atributos del puesto, no de la ubicación de la
 *     persona en la organización, y ninguno cambia lo que hacés con la ficha.
 */
export interface DatoClave {
  label: string
  valor: string
}

/**
 * Antigüedad legible, o la fecha de ingreso futura si todavía no entró.
 *
 * 🔴 UN PREINGRESO NO TIENE ANTIGÜEDAD, y calcularla igual daría "0 meses" o —peor— un número
 * negativo redondeado a cero, que se leería como "entró hoy". Alguien que todavía no empezó
 * necesita ver CUÁNDO empieza, que es la pregunta que se hace quien abre esa ficha.
 */
export function antiguedad(fechaIngreso: string | null | undefined, hoy = hoyISO()): string {
  if (!fechaIngreso) return "—"
  if (fechaIngreso > hoy) {
    const [a, m, d] = fechaIngreso.split("-")
    return `Ingresa el ${d}/${m}/${a}`
  }
  const meses =
    (Number(hoy.slice(0, 4)) - Number(fechaIngreso.slice(0, 4))) * 12 +
    (Number(hoy.slice(5, 7)) - Number(fechaIngreso.slice(5, 7))) -
    (Number(hoy.slice(8, 10)) < Number(fechaIngreso.slice(8, 10)) ? 1 : 0)
  if (meses < 1) return "Menos de un mes"
  if (meses < 12) return `${meses} ${meses === 1 ? "mes" : "meses"}`
  const anios = Math.floor(meses / 12)
  const resto = meses % 12
  const base = `${anios} ${anios === 1 ? "año" : "años"}`
  return resto === 0 ? base : `${base} y ${resto} ${resto === 1 ? "mes" : "meses"}`
}

export function datosClave(empleado: Empleado): DatoClave[] {
  return [
    { label: "Empresa", valor: empleado.empresa_nombre ?? "—" },
    { label: "Área", valor: empleado.area_nombre ?? "—" },
    { label: "Superior", valor: empleado.manager_nombre ?? "Sin asignar" },
    { label: "Antigüedad", valor: antiguedad(empleado.fecha_ingreso) },
  ]
}
