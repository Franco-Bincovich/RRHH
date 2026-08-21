// Mapeos, clases y helpers de presentación compartidos por las piezas de sucesión.
// Módulo sin JSX a propósito (mismo rol que reportes/catalogo.ts): lo importan la página,
// las dos tabs y los dos modales, así que no puede arrastrar componentes.

import type { EmpleadoCelda } from "./NineBox"
import type { EmpleadoMapa } from "@/types/sucesion"

// ─── Mapeos 9-Box ─────────────────────────────────────────────────────────────

const POTENCIAL_FILA: Record<EmpleadoMapa["potencial"], 0 | 1 | 2> = {
  alto: 0, medio: 1, bajo: 2,
}
const DESEMPENO_COL: Record<EmpleadoMapa["desempeno"], 0 | 1 | 2> = {
  bajo: 0, medio: 1, alto: 2,
}

export function toEmpleadoCelda(e: EmpleadoMapa): EmpleadoCelda {
  return {
    id: e.id,
    nombre: `${e.nombre} ${e.apellido}`.trim(),
    cargo: e.cargo ?? "",
    area: e.area_nombre ?? "",
    fila: POTENCIAL_FILA[e.potencial],
    columna: DESEMPENO_COL[e.desempeno],
  }
}

// ─── Clases ───────────────────────────────────────────────────────────────────

/*
 * 🔴 LOS COLORES SALEN DE LA PALETA SEMÁNTICA, NO DE LA ESCALA CRUDA DE TAILWIND.
 *
 * Acá decía `bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 …`: seis valores escritos a
 * mano por nivel, elegidos de la escala de Tailwind y no de la paleta del sistema. Eso tiene dos
 * consecuencias que no son estéticas:
 *   · el contraste de esos pares NO lo mide `app/contrasteTokens.test.ts`, que barre los diez
 *     pares fondo/texto de la paleta en los dos temas. Un `emerald-800` sobre `emerald-100` puede
 *     quedar por debajo del mínimo WCAG y nadie se entera.
 *   · un ajuste de la paleta —el del 19/8 subió tres pares— deja estos colores donde estaban, así
 *     que "verde" empieza a significar dos verdes distintos según la pantalla.
 *
 * ⚠️ NO es el caso de los 26 hex de `colorEmpresa` en /organigrama: aquéllos son IDENTIDAD (cada
 * empresa su color, sin orden ni significado) y por eso se dejan como están. Estos tres son
 * ESTADO en una escala mal→bien, que es exactamente lo que el par danger/warning/success nombra.
 */
export const NIVEL_BADGE_CLASS: Record<string, string> = {
  alto: "bg-success-wash text-success",
  medio: "bg-warning-wash text-warning",
  bajo: "bg-danger-wash text-destructive",
}

// La barra de readiness es un relleno sólido, no un par fondo/texto: usa el color fuerte de cada
// tramo. El corte en 70/40 no se tocó — es la definición del módulo, no una decisión de color.
export function readinessBarColor(pct: number): string {
  if (pct >= 70) return "bg-success"
  if (pct >= 40) return "bg-warning"
  return "bg-destructive"
}
