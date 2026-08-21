import { formatFecha } from "@/components/features/shared/fechas"
import type { EntradaHistorial } from "@/components/ui/Historial"
import type { Recategorizacion } from "@/types/recategorizacion"

/**
 * Cómo se LEE una recategorización: qué cambió de verdad, y cómo se escribe el monto.
 *
 * Puro y sin React: es lo que hace que las tres decisiones de abajo se puedan desmentir sin
 * renderizar nada (vitest corre sin jsdom).
 */

/** Un par "de → a" de los tres que una recategorización puede tener. */
export interface ParCambio {
  clave: string
  /** "Rol", "Seniority", "Categoría". */
  label: string
  /** El valor previo. `null` cuando no había ninguno: ahí no hay "de" que mostrar. */
  desde: string | null
  hasta: string
}

const PARES = [
  { clave: "rol", label: "Rol", anterior: "rol_anterior", nuevo: "rol_nuevo" },
  { clave: "seniority", label: "Seniority", anterior: "seniority_anterior", nuevo: "seniority_nueva" },
  { clave: "categoria", label: "Categoría", anterior: "categoria_anterior", nuevo: "categoria_nueva" },
] as const

/**
 * Los pares que EFECTIVAMENTE cambiaron, en el orden fijo rol → seniority → categoría.
 *
 * 🔴 UN PAR SIN VALOR NUEVO NO SE MUESTRA, y ese es todo el punto de esta función. Una
 * recategorización cambia UNO de los tres campos la mayoría de las veces, así que dibujar los
 * tres siempre llenaría dos tercios de la celda con "— → —" (o, peor, con "null → null"). El
 * CHECK de la migración 117 garantiza que al menos uno viene cargado, así que el resultado nunca
 * es una lista vacía.
 *
 * ⚠️ EL DISPARADOR ES EL VALOR **NUEVO**, no la diferencia entre los dos. Una fila puede traer
 * `rol_anterior` cargado y `rol_nuevo` en `null` —significa "el rol no se tocó en este cambio",
 * y el anterior está ahí porque el backend lo copia de la cadena—, y ahí no hubo cambio de rol.
 * Comparar `anterior !== nuevo` marcaría esa fila como si el rol se hubiera borrado.
 *
 * ⚠️ `desde` puede ser `null` con `hasta` cargado: es el primer valor que esa persona tuvo en ese
 * campo. Se muestra sin flecha, no con un "— →" que se lee como si antes hubiera habido algo.
 */
export function paresCambiados(r: Recategorizacion): ParCambio[] {
  const fila = r as unknown as Record<string, string | null>
  return PARES.filter((p) => fila[p.nuevo]).map((p) => ({
    clave: p.clave,
    label: p.label,
    desde: fila[p.anterior] || null,
    hasta: fila[p.nuevo] as string,
  }))
}

/**
 * El impacto salarial, legible.
 *
 * 🔴 ES UN MONTO EN PESOS Y NUNCA UN PORCENTAJE (§7). Y llega como STRING —Pydantic serializa
 * `Decimal` a string—, así que se PARSEA antes de formatear: llamar `toLocaleString()` sobre el
 * string devuelve el string tal cual, sin separador de miles y sin ningún error a la vista.
 *
 * Un monto negativo es válido (una recategorización puede bajar un sueldo) y sale con su signo.
 * `null` → cadena vacía: quien llama decide si eso es "no se cargó" o "no lo podés ver", que
 * desde acá no se distinguen a propósito.
 */
export function montoLegible(impacto: string | null): string {
  if (impacto === null || impacto === "") return ""
  const n = Number(impacto)
  if (!Number.isFinite(n)) return impacto
  const abs = Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".")
  return n < 0 ? `-$${abs}` : `$${abs}`
}

/**
 * El historial de la ficha: UNA entrada por recategorización, para `components/ui/Historial`.
 *
 * 🔴 UNA ENTRADA POR RECATEGORIZACIÓN Y NO UNA POR PAR CAMBIADO, aunque un cambio pueda tocar los
 * tres campos. `Historial` marca "Vigente" en la PRIMERA entrada de la lista, y ese chip tiene que
 * significar "esta es la recategorización vigente": con una entrada por par, un cambio que tocó
 * rol y seniority pondría "Vigente" en el rol y dejaría la seniority del mismo cambio sin marcar,
 * como si fuera vieja. Los pares se juntan con " · " en las dos puntas del "de → a".
 *
 * El `detalle` es el MOTIVO: en la ficha, la pregunta que sigue a "qué cambió" es "por qué", y es
 * el único lugar donde ese texto se ve sin abrir la planilla. Si es largo, la línea envuelve —
 * `Historial` ya trae `flex-wrap` para eso.
 *
 * La lista llega ORDENADA de más reciente a más antigua (así la devuelve el backend) y se
 * conserva: reordenar acá rompería el significado del chip.
 */
export function entradasHistorial(items: Recategorizacion[]): EntradaHistorial[] {
  return items.map((r) => {
    const pares = paresCambiados(r)
    const desde = pares.map((p) => p.desde).filter(Boolean).join(" · ")
    return {
      clave: r.id,
      fecha: formatFecha(r.fecha_efectiva),
      // Vacío → `null`: si ninguno de los pares tenía valor previo, no hay "de" que mostrar.
      desde: desde || null,
      hasta: pares.map((p) => p.hasta).join(" · "),
      detalle: r.motivo,
    }
  })
}
