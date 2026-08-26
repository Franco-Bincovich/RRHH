import {
  ArrowLeftRight, Briefcase, Building2, CalendarOff, CalendarX2, Hourglass, LogOut, UserPlus,
  Users, Wallet,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"

import type { KpisExtra } from "@/services/dashboard"
import type { UserRol } from "@/types/auth"
import { destino } from "./_destinosKpi"
import { kpiOculto } from "./_ocultoEnDashboard"
import type { DatosAdmin } from "./dashboardAdminData"

/**
 * LOS DIEZ KPIs de §6, en sus dos bloques y en su orden. Se DECLARAN los diez y se pintan los que
 * `_ocultoEnDashboard` no esconde — hoy NUEVE: la masa salarial se fue de la vista con Costos.
 *
 * El orden NO es libre: es el del documento, y `dashboardBloques.test.tsx` lo fija contra una
 * lista escrita a mano. Un KPI que se agregue por gusto rompe ese test, que es el punto.
 *
 * 🔴 TRES REGLAS QUE ESTE ARCHIVO SOSTIENE, y las tres nacieron de un número que mentía:
 *
 * 1. **Una card nunca afirma un dato que no tiene.** Si el KPI viene en `kpis_extra.errores` —el
 *    fail-safe por KPI del backend devolvió su vacío— la card muestra `—`, no el `0` que llegó.
 *    Si la masa salarial no tiene NADA cargado, dice "Sin cargar", no "$0". Y si no hay mes
 *    anterior, la variación dice que no hay con qué comparar, no "+0%".
 * 2. **El fondo semántico es para lo ACCIONABLE, no para lo llamativo.** Ver `_tonoIngresos`:
 *    hoy hay UNA sola card que se despega, y el umbral no está inventado.
 * 3. **`kpis.bajas_mes` y `kpis.ingresos_mes` NO tienen card propia.** Entran como la línea de
 *    contraste de la card de §6 a la que pertenecen (el mes contra los 12 meses, lo que ya pasó
 *    contra lo que viene). Meterlos como cards habría dado DOCE, y §6 pide diez.
 *    `kpis.onboardings_activos` no entra a esta pantalla: su lugar es /onboarding.
 */

export type TonoKpi = "neutro" | "atencion" | "riesgo" | "bien"

export interface KpiCardData {
  title: string
  value: string
  icon: LucideIcon
  description: string
  tono: TonoKpi
  /** Filas chicas debajo del valor. Hoy solo las usa el headcount por empresa. */
  detalle?: { etiqueta: string; valor: string }[]
  /**
   * A dónde lleva la card. `undefined` = no lleva a ningún lado y no se pinta como control.
   * NO se escribe card por card: lo pone `bloquesKpi` al final, leyendo `_destinosKpi`, que es
   * donde vive también el chequeo de permiso. Ver el 🔴 de ese archivo.
   */
  href?: string
}

export interface BloqueKpi {
  titulo: string
  kpis: KpiCardData[]
}

/** Lo que se muestra donde no hay dato. Un guion no se confunde con un cero medido. */
export const SIN_DATO = "—"

const nf = (d: number) => new Intl.NumberFormat("es-AR", {
  minimumFractionDigits: d, maximumFractionDigits: d,
})

function moneda(value: number): string {
  return new Intl.NumberFormat("es-AR", {
    style: "currency", currency: "ARS", maximumFractionDigits: 0,
  }).format(value)
}

/**
 * 🔴 `null` NO ES CERO. `null` = no hay mes anterior cargado contra el cual comparar; `0` = hay
 * base y la masa salarial no se movió. Antes del 21/8/2026 los dos llegaban como `0` y esta
 * función pintaba "+0% vs mes anterior" — una afirmación falsa, y la más creíble de todas.
 */
export function formatVariacion(pct: number | null): string {
  if (pct === null) return "Sin mes anterior para comparar"
  return `${pct > 0 ? "+" : ""}${nf(1).format(pct)}% vs mes anterior`
}

/** Un KPI que el backend no pudo calcular NO se pinta como un cero medido. */
function conFallo(x: KpisExtra, clave: string, card: KpiCardData): KpiCardData {
  return x.errores.includes(clave)
    ? { ...card, value: SIN_DATO, description: "No se pudo calcular", tono: "neutro" }
    : card
}

/**
 * El ÚNICO tono no neutro de la pantalla, y el umbral no es inventado: es el que el backend ya
 * usa para levantar una alerta. Si `/atencion` trae al menos un `ingreso_proximo` —o sea alguien
 * que entra dentro de los 7 días de `VENTANA_DIAS`, o que debía entrar y sigue en preingreso— la
 * card de los 30 días se despega, porque esta semana hay legajos que activar.
 *
 * Por qué no "más de 0 en 30 días": una vez que RRHH cargue preingresos, esa card quedaría en
 * ámbar SIEMPRE, y una card que siempre grita deja de decir nada. Por qué no un número fijo
 * ("más de 5 ingresos es mucho"): no existe en el sistema, y §6 pide despegar lo que requiere
 * ACCIÓN, no lo que es grande.
 *
 * ⚠️ Si `/atencion` falló, `atencionError` es true y la card queda NEUTRA: no se puede afirmar
 * que no hay nada urgente, pero pintarla de ámbar por las dudas sería inventar la alerta.
 */
function _tonoIngresos(datos: DatosAdmin): TonoKpi {
  if (datos.atencionError) return "neutro"
  return datos.atencion.some((a) => a.tipo === "ingreso_proximo") ? "atencion" : "neutro"
}

function bloqueOperacion(datos: DatosAdmin): KpiCardData[] {
  const { kpis: k, kpis_extra: x } = datos.dashboard
  return [
    { title: "Colaboradores activos", value: String(k.empleados_activos), icon: Users,
      description: "En plantilla hoy", tono: "neutro" },
    { title: "Búsquedas abiertas", value: String(k.vacantes_activas), icon: Briefcase,
      description: "Posiciones sin cubrir", tono: "neutro" },
    { title: "Ingresos próximos 30 días", value: String(x.ingresos_proximos_30), icon: UserPlus,
      // El contraste es `ingresos_mes`: lo que YA entró este mes contra lo que viene.
      description: `${k.ingresos_mes} ya ingresaron este mes`, tono: _tonoIngresos(datos) },
    conFallo(x, "ausencias_activas_hoy",
      { title: "Ausencias en curso", value: String(x.ausencias_activas_hoy), icon: CalendarOff,
        description: "Colaboradores ausentes hoy", tono: "neutro" }),
    conFallo(x, "recategorizaciones_mes",
      { title: "Recategorizaciones del mes", value: String(x.recategorizaciones_mes),
        icon: ArrowLeftRight, description: "Con fecha efectiva en el mes", tono: "neutro" }),
    conFallo(x, "rotacion_12m",
      { title: "Rotación 12 meses", value: `${nf(1).format(x.rotacion_12m_pct)}%`, icon: LogOut,
        // El contraste es `bajas_mes`: el mes contra los doce meses.
        description: `${x.rotacion_12m_bajas} bajas en 12 meses · ${k.bajas_mes} este mes`,
        tono: "neutro" }),
  ]
}

/**
 * "Sin cargar" ≠ "$0". Con `costos_nomina` vacía los dos meses dan 0 y la variación llega `null`,
 * y las tres condiciones juntas solo pueden significar que no hay nada cargado: una nómina real
 * de 31 personas no suma cero. Un mes que CAE a cero teniendo mes anterior no cae acá — ahí la
 * variación es -100 % y el `$0` es verdad.
 * ⚠️ HOY NO SE PINTA (`_ocultoEnDashboard`): sus reglas se conservan enteras y testeadas, así
 * que el día que Costos vuelva al menú la card vuelve sabiendo no afirmar un cero. */
export function masaSalarial(x: KpisExtra): KpiCardData {
  const sinCargar = x.masa_salarial_actual === 0 && x.masa_salarial_anterior === 0
    && x.masa_salarial_variacion_pct === null
  return conFallo(x, "masa_salarial", {
    title: "Masa salarial del mes",
    value: sinCargar ? SIN_DATO : moneda(x.masa_salarial_actual),
    icon: Wallet,
    description: sinCargar ? "Sin costos cargados" : formatVariacion(x.masa_salarial_variacion_pct),
    tono: "neutro",
  })
}

function bloquePeriodo(datos: DatosAdmin): KpiCardData[] {
  const { kpis_extra: x, headcount_por_empresa: empresas } = datos.dashboard
  return [
    masaSalarial(x),
    conFallo(x, "ausentismo_mes",
      // El 0 % de ausentismo SÍ se muestra como 0: sin licencias cargadas, "nadie faltó" y "no
      // hay datos" son la misma respuesta, al revés que en la masa salarial. La nota del backend
      // dice sobre qué base de días hábiles se calculó.
      { title: "Ausentismo del mes", value: `${nf(1).format(x.ausentismo_mes_pct)}%`,
        icon: CalendarX2, description: x.ausentismo_nota || "Sobre los días hábiles del mes",
        tono: "neutro" }),
    conFallo(x, "antiguedad",
      // §6 pide el PROMEDIO: ese es el número grande. La mediana va de contraste porque con los
      // datos reales el promedio de una de las dos empresas es 61 % más alto por UNA persona.
      { title: "Antigüedad promedio", value: `${nf(1).format(x.antiguedad_promedio_anios)} años`,
        icon: Hourglass,
        description: `Mediana: ${nf(1).format(x.antiguedad_mediana_anios)} años`,
        tono: "neutro" }),
    { title: "Headcount por empresa",
      // El total repite `empleados_activos` A PROPÓSITO: es el mismo universo partido por
      // sociedad, y que cierren es un invariante que el backend testea. El dato de la card es
      // el reparto de abajo.
      value: empresas.length ? String(empresas.reduce((t, e) => t + e.total, 0)) : SIN_DATO,
      icon: Building2,
      description: empresas.length
        ? `Repartidos en ${empresas.length} ${empresas.length === 1 ? "sociedad" : "sociedades"}`
        : "Sin datos",
      tono: "neutro",
      detalle: empresas.map((e) => ({ etiqueta: e.empresa, valor: String(e.total) })) },
  ]
}

/**
 * 🔴 `rol` ES OBLIGATORIO Y NO TIENE DEFAULT. Un `rol = null` por defecto sería fail-closed —o
 * sea, correcto— pero dejaría que un caller se olvide de pasarlo y la pantalla quede SIN NINGÚN
 * link, en verde y sin que nada rojee: el verde vacuo que este repo ya pagó cinco veces. Que
 * falte es un error de compilación. La página lo tiene resuelto antes de montar el dashboard
 * (`useRol` en `app/(dashboard)/dashboard/page.tsx`), así que nunca es `null` acá.
 *
 * El destino se cuelga al FINAL y en un solo lugar, no dentro de cada literal de card: las diez
 * cards siguen diciendo solo qué muestran, a dónde llevan lo decide `_destinosKpi` y si se
 * pintan, `_ocultoEnDashboard` — que deriva las dos cosas de `RUTAS_OCULTAS`.
 */
export function bloquesKpi(datos: DatosAdmin, rol: UserRol | null): BloqueKpi[] {
  const visibles = (kpis: KpiCardData[]) =>
    kpis.filter((k) => !kpiOculto(k.title)).map((k) => ({ ...k, href: destino(rol, k.title) }))
  return [
    { titulo: "Operación", kpis: visibles(bloqueOperacion(datos)) },
    { titulo: "Indicadores del período", kpis: visibles(bloquePeriodo(datos)) },
  ]
}
