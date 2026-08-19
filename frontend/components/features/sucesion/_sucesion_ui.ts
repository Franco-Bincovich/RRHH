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

// Clase del badge de nivel (potencial/desempeño). El <span> que la usa vive en
// AnalisisAreaModal, su único consumidor: acá no entra JSX.
export const NIVEL_BADGE_CLASS: Record<string, string> = {
  alto: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
  medio: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  bajo: "bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-300",
}

export function readinessBarColor(pct: number): string {
  if (pct >= 70) return "bg-emerald-500"
  if (pct >= 40) return "bg-amber-500"
  return "bg-rose-500"
}
