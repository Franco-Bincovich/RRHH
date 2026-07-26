import { Briefcase, CalendarDays, DollarSign, PieChart, RefreshCw, UserCheck, UserPlus, Users } from "lucide-react"

import { ReporteCard, type ReporteEstandar } from "./ReporteCard"

// Catálogo de reportes estándar (descargables PDF/Excel). El reporte Ad Hoc con IA quedó oculto
// del catálogo (su backend/endpoint siguen vivos para reactivar).
const REPORTES_ESTANDAR: ReporteEstandar[] = [
  {
    id: "headcount",
    titulo: "Reporte de Headcount",
    descripcion:
      "Evolución de la dotación por área, nivel y tipo de contratación. Incluye altas, bajas y transferencias del período.",
    icon: Users,
    usaPeriodo: true,
  },
  {
    id: "rotacion",
    titulo: "Reporte de Rotación",
    descripcion:
      "Índice de rotación voluntaria e involuntaria, análisis de causas de egreso y comparativa histórica por trimestre.",
    icon: RefreshCw,
    usaPeriodo: true,
  },
  {
    id: "altas_bajas",
    titulo: "Altas y bajas",
    descripcion:
      "Listado nominal de ingresos y egresos del período: nombre, área y fecha (y motivo en las bajas).",
    icon: UserPlus,
    usaPeriodo: true,
  },
  {
    id: "distribucion",
    titulo: "Distribución de plantilla",
    descripcion:
      "Composición de la dotación activa por seniority, modalidad de contratación y turno. Los no especificados se agrupan aparte.",
    icon: PieChart,
    usaPeriodo: false,
  },
  {
    id: "costos",
    titulo: "Reporte de Costos",
    descripcion:
      "Nómina total y por área, desvío presupuestario, costo promedio por empleado y evolución mensual del período.",
    icon: DollarSign,
    usaPeriodo: true,
  },
  {
    id: "vacantes",
    titulo: "Reporte de Vacantes",
    descripcion:
      "Estado del pipeline de selección, tiempo promedio de cobertura, vacantes activas y cerradas por área.",
    icon: Briefcase,
    usaPeriodo: false,
  },
  {
    id: "onboarding",
    titulo: "Reporte de Onboarding",
    descripcion:
      "Completitud de tareas de inducción, tiempo promedio al primer hito productivo y encuestas de experiencia de ingreso.",
    icon: UserCheck,
    usaPeriodo: false,
  },
  {
    id: "anual_consolidado",
    titulo: "Informe Anual Consolidado",
    descripcion:
      "Resumen del año completo: ingresos, egresos, headcount por área, procesos, vacaciones, capacitaciones y evaluaciones. Exporta a Excel con múltiples hojas.",
    icon: CalendarDays,
    usaPeriodo: false,
    usaAnio: true,
  },
]

export function ReportesCatalogo({
  canWrite,
  onGenerado,
}: {
  canWrite: boolean
  onGenerado: () => void
}) {
  return (
    <section aria-label="Reportes disponibles">
      <h2 className="mb-4 text-base font-semibold text-foreground">Reportes disponibles</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {REPORTES_ESTANDAR.map((r) => (
          <ReporteCard key={r.id} reporte={r} canWrite={canWrite} onSuccess={onGenerado} />
        ))}
      </div>
    </section>
  )
}
