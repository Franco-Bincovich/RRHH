import { Briefcase, CalendarDays, CalendarOff, ClipboardList, DollarSign, GraduationCap, Palmtree, PieChart, RefreshCw, ScrollText, Target, UserCheck, UserPlus, Users } from "lucide-react"

import type { ReporteEstandar } from "./ReporteCard"

// Catálogo de reportes estándar (descargables PDF/Excel). El reporte Ad Hoc con IA quedó oculto
// del catálogo (su backend/endpoint siguen vivos para reactivar).
// usaArea default true; false solo en reportes transversales (anual, auditoría).
export const REPORTES_ESTANDAR: ReporteEstandar[] = [
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
    usaArea: false, // consolidado transversal: no aplica filtro por área
  },
  {
    id: "saldos_vacaciones",
    titulo: "Saldos de vacaciones",
    descripcion:
      "Por empleado: días asignados, tomados (los cancelados no restan) y saldo disponible. Marca a quienes no tienen días asignados.",
    icon: Palmtree,
    usaPeriodo: true,
  },
  {
    id: "ausentismo",
    titulo: "Ausentismo por área",
    descripcion:
      "Días de ausencia totales e injustificados por área, con sus tasas % sobre 22 días hábiles/mes. Elegí qué métrica ver.",
    icon: CalendarOff,
    usaPeriodo: true,
    usaVista: true,
  },
  {
    id: "listado_vac_aus",
    titulo: "Vacaciones y ausencias",
    descripcion:
      "Listado plano de todas las vacaciones y ausencias del período: empleado, área, tipo, fechas, días y motivo/estado.",
    icon: ClipboardList,
    usaPeriodo: true,
  },
  {
    id: "presupuesto",
    titulo: "Presupuesto vs real",
    descripcion:
      "Por área: monto presupuestado, ejecutado, desvío y % de ejecución del período. Muestra sobre y sub ejecución.",
    icon: Target,
    usaPeriodo: true,
  },
  {
    id: "capacitacion",
    titulo: "Capacitación por área",
    descripcion:
      "Asignaciones de capacitación del período por área: completadas, en curso, pendientes y horas totales.",
    icon: GraduationCap,
    usaPeriodo: true,
  },
  {
    id: "auditoria",
    titulo: "Trazabilidad / Auditoría",
    descripcion:
      "Log de auditoría del período: fecha, usuario, entidad, evento y acción. Exportable a PDF/Excel.",
    icon: ScrollText,
    usaPeriodo: true,
    usaArea: false, // la auditoría no tiene área
  },
]
