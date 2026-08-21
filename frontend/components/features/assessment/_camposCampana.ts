import type { TipoEval } from "@/types/assessment"

/**
 * Los tres tipos de evaluación que una campaña puede tener. Módulo de datos sin JSX: vivía dentro
 * de `CampanaModal.tsx` y se mudó con los campos, que son su único consumidor.
 *
 * Las etiquetas dicen qué entra en cada tipo entre paréntesis a propósito: "Completo" a secas no
 * distingue de "Conductual" para quien no conoce el modelo AREAS, y esta lista es lo único que
 * el usuario tiene a mano para elegir.
 */
export const TIPOS: { value: TipoEval; label: string }[] = [
  { value: "completo",   label: "Completo (AREAS + Cognitivo + Técnico)" },
  { value: "conductual", label: "Conductual (AREAS)" },
  { value: "cognitivo",  label: "Cognitivo" },
]
