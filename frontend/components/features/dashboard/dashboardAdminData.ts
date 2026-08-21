import {
  fetchAtencion, fetchDashboard,
  type AlertaAtencion, type AlertaDashboard, type DashboardData,
} from "@/services/dashboard"

/**
 * Los datos del dashboard de admin: la carga y los helpers de presentación (sin JSX).
 *
 * La carga vive acá y no en `DashboardAdmin` porque desde A6 son DOS endpoints con dos paneles
 * distintos, y quien decide qué pasa si uno de los dos falla es una regla de datos, no del
 * componente que los pinta. Ver `cargarDatosAdmin`.
 *
 * 🔴 EL CATÁLOGO DE KPIs SE FUE a `_kpisDashboard.ts` (21/8/2026), y el corte no es por líneas:
 * son dos preguntas distintas. Acá vive **cómo se traen los datos y qué pasa si un endpoint
 * falla**; allá, **qué card muestra qué y cuándo se despega**. `_kpisDashboard` importa el
 * `DatosAdmin` de este archivo y no al revés — este no sabe que existen las cards.
 */

export const NIVEL_VARIANT: Record<AlertaDashboard["nivel"], "default" | "secondary" | "destructive"> = {
  info:    "secondary",
  warning: "default",
  error:   "destructive",
}

export const NIVEL_LABEL: Record<AlertaDashboard["nivel"], string> = {
  info:    "Info",
  warning: "Aviso",
  error:   "Urgente",
}

/**
 * Los datos de los dos paneles de avisos, en una sola carga.
 *
 * 🔴 FAIL-SAFE POR ENDPOINT, igual que el `_safe` por KPI del backend: si `/atencion` falla, el
 * dashboard entero se muestra lo mismo y solo ese panel queda vacío y marcado. Al revés no: si
 * falla `/api/dashboard` no hay dashboard que mostrar, así que ese error se propaga.
 *
 * Las dos llamadas van EN PARALELO. Encadenarlas sumaría la latencia de la segunda a la primera
 * sin ninguna razón: no dependen entre sí, ni siquiera comparten filtro — las dos leen la
 * empresa activa del mismo header que `apiFetch` ya inyecta.
 */
export interface DatosAdmin {
  dashboard: DashboardData
  atencion: AlertaAtencion[]
  /** `true` = el panel de atención no pudo cargar. Distinto de "cargó y no hay nada". */
  atencionError: boolean
}

export async function cargarDatosAdmin(): Promise<DatosAdmin> {
  const [dashboard, atencion] = await Promise.all([
    fetchDashboard(),
    fetchAtencion().then((r) => r.alertas).catch(() => null),
  ])
  return { dashboard, atencion: atencion ?? [], atencionError: atencion === null }
}
