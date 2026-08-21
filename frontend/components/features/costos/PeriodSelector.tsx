/**
 * ⚠️ EL COMPONENTE SE MUDÓ A `components/features/shared/PeriodSelector.tsx` al aparecer su
 * segundo consumidor (`/horas-por-cliente`). Este archivo lo RE-EXPORTA para que los imports
 * existentes de costos no cambien: el corte fue de dónde vive el código, no de quién lo usa.
 * Mismo movimiento que `grillaTabla` hizo con `Encabezado` y `FilasEsqueleto`.
 */
export { PeriodSelector } from "@/components/features/shared/PeriodSelector"
