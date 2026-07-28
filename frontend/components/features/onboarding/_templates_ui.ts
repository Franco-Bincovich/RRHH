/**
 * Primitivas compartidas entre la página de detalle de un template y sus componentes.
 *
 * Las 4 semanas son el eje del proceso de onboarding y están fijas en el modelo: la columna
 * `onboarding_tareas.semana` tiene un CHECK (semana BETWEEN 1 AND 4) desde la migración 027.
 * El tipo literal es el mismo que acepta `addTarea` en services/onboarding.ts — vive acá para
 * que la página y los componentes no lo declaren cada uno por su lado y se desincronicen del
 * CHECK.
 */
export const SEMANAS = [1, 2, 3, 4] as const

export type Semana = (typeof SEMANAS)[number]
