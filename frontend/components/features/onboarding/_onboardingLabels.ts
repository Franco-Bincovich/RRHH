import type { OnboardingInstancia } from "@/types/onboarding"

/**
 * La etiqueta de avance de un proceso de onboarding.
 *
 * Salió de la página al partirla. Es pura, así que además se puede testear sin renderizar.
 *
 * ⚠️ LA SEMANA SE DEDUCE DEL PORCENTAJE DE TAREAS, no de una fecha: el modelo no guarda en qué
 * semana está cada proceso, guarda cuántas tareas de su checklist se completaron. Cuatro semanas
 * es el largo del template estándar, y por eso el divisor es 4. Si un template tuviera otro
 * largo, esta etiqueta lo aproximaría — está declarado acá para que se lea antes de confiar en
 * el número.
 */
export function semanaLabel(inst: OnboardingInstancia): string {
  if (inst.progreso >= 100) return "Completado"
  if (inst.tareas_total === 0) return "Semana 1"
  const semanasCompletadas = Math.floor(inst.tareas_completadas / (inst.tareas_total / 4))
  return `Semana ${Math.min(semanasCompletadas + 1, 4)}`
}

