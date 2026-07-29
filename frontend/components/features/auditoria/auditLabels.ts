/**
 * Etiquetas y formateo legibles para la UI de auditoría (T18.5c).
 * Traduce entidades/eventos/campos técnicos a lenguaje sin jerga y formatea valores.
 */

export const ENTIDAD_LABEL: Record<string, string> = {
  empleado: "Empleado",
  vacacion: "Vacación",
  ausencia: "Ausencia",
  nomina: "Nómina",
  presupuesto: "Presupuesto",
  empresa: "Empresa",
  offboarding: "Offboarding",
}

export const EVENTO_LABEL: Record<string, string> = {
  alta_empleado: "Alta de empleado",
  update_empleado: "Modificación de empleado",
  baja_empleado: "Baja de empleado",
  cancelacion_vacacion: "Cancelación de vacación",
  alta_ausencia: "Alta de ausencia",
  update_ausencia: "Modificación de ausencia",
  baja_ausencia: "Baja de ausencia",
  inicio_offboarding: "Inicio de offboarding",
  devolucion_activo: "Devolución de activo",
  carga_nomina: "Carga de nómina",
  set_presupuesto: "Configuración de presupuesto",
  alta_empresa: "Alta de empresa",
  toggle_empresa_activa: "Activación/desactivación de empresa",
}

/**
 * Campos que un *Response trae resueltos por join o calculados, y que NO son datos del
 * registro. El backend dejó de escribirlos en los diffs, pero los eventos YA GUARDADOS los
 * tienen: 93 eventos de modificación de empleado dicen que el área y la empresa pasaron a
 * vacío, y ninguna de las dos cambió — era el resultado de leer el "antes" con joins y el
 * "después" sin ellos.
 *
 * Esos eventos NO se borran: un log del que se sacan las filas incómodas deja de ser
 * auditoría. Se filtran al renderizar, en un solo lugar, para que la pantalla no le afirme al
 * usuario un cambio que no ocurrió.
 *
 * ⚠️ Aplica SOLO a eventos anteriores al fix. Los nuevos ya no traen estas claves, así que el
 * filtro no les saca nada. El día que no queden eventos viejos, esto se puede borrar entero.
 */
const CAMPOS_DERIVADOS = new Set([
  "area_nombre", "empresa_nombre", "empleado_nombre", "manager_nombre", "tipo_nombre",
])

/** Claves con contenido real de un diff: las derivadas quedan afuera. */
export function clavesVisibles(
  antes: Record<string, unknown> | null,
  nuevos: Record<string, unknown> | null,
): string[] {
  const todas = new Set([...Object.keys(antes ?? {}), ...Object.keys(nuevos ?? {})])
  return Array.from(todas).filter((k) => !CAMPOS_DERIVADOS.has(k))
}

/** True si el evento traía datos pero TODOS eran derivados: se editó sin tocar nada auditado. */
export function soloTraiaDerivados(
  antes: Record<string, unknown> | null,
  nuevos: Record<string, unknown> | null,
): boolean {
  const habia = Object.keys(antes ?? {}).length + Object.keys(nuevos ?? {}).length > 0
  return habia && clavesVisibles(antes, nuevos).length === 0
}

export const SIN_CAMBIOS_AUDITADOS = "Se editó el registro, sin cambios en campos auditados."

const CAMPO_LABEL: Record<string, string> = {
  nombre: "Nombre",
  apellido: "Apellido",
  legajo: "Legajo",
  roles: "Roles",
  cargo: "Cargo", // histórico: registros previos a la unificación de roles (S4)
  area_id: "Área",
  seniority: "Seniority",
  estado: "Estado",
  // Columnas reales que el diff volvió a registrar al dejar de enumerar una lista curada.
  manager_id: "Superior",
  dni: "DNI",
  cuil: "CUIL",
  email_corporativo: "Email corporativo",
  email_personal: "Email personal",
  telefono: "Teléfono",
  fecha_ingreso: "Fecha de ingreso",
  fecha_egreso: "Fecha de egreso",
  fecha_nacimiento: "Fecha de nacimiento",
  tipo_contrato: "Tipo de contrato",
  modalidad_trabajo: "Modalidad de trabajo",
  turno: "Turno",
  dias_vacaciones_asignados: "Días de vacaciones asignados",
  comentario: "Comentario",
  cancelada: "Cancelada",
  tipo: "Tipo",
  activa: "Activa",
  fecha_desde: "Desde",
  fecha_hasta: "Hasta",
  dias: "Días",
  justificada: "Justificada",
  motivo: "Motivo",
  tipo_id: "Tipo",
  empleado_id: "Empleado",
  mes: "Mes",
  anio: "Año",
  monto_bruto: "Monto bruto",
  monto_neto: "Monto neto",
  presupuesto: "Presupuesto",
  cuit: "CUIT",
  motivo_egreso: "Motivo de egreso",
  devuelto: "Devuelto",
  activo_id: "Activo",
}

/** Etiqueta legible de un campo; fallback al nombre crudo si no está mapeado. */
export function campoLabel(campo: string): string {
  return CAMPO_LABEL[campo] ?? campo
}

/** Formatea un valor de payload: lista→"a, b, c", bool→Sí/No, fecha ISO→dd/mm/yyyy, vacío→"—", resto→texto. */
export function formatValor(v: unknown): string {
  if (Array.isArray(v)) return v.length ? v.join(", ") : "—"
  if (v === null || v === undefined || v === "") return "—"
  if (typeof v === "boolean") return v ? "Sí" : "No"
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}/.test(v)) {
    const [y, m, d] = v.slice(0, 10).split("-")
    return `${d}/${m}/${y}`
  }
  return String(v)
}

/**
 * Formatea el valor de un campo resolviendo los ids que no le dicen nada a nadie.
 *
 * Hoy solo `area_id`, que el diff guarda como UUID porque es la columna real (el nombre lo
 * resuelve un join, y los nombres de join NO van en un diff — ver CAMPOS_DERIVADOS). La
 * traducción va acá, al renderizar, y no en lo que se guarda: así también quedan legibles los
 * eventos YA GUARDADOS, que tienen el UUID adentro y no se van a reescribir.
 *
 * ⚠️ MUESTRA EL NOMBRE ACTUAL DEL ÁREA, NO EL QUE TENÍA CUANDO SE HIZO EL CAMBIO. Si un área
 * se renombra, los eventos viejos pasan a mostrar el nombre nuevo. Es una consecuencia
 * deliberada de resolver al leer: la alternativa —congelar el nombre al escribir— solo
 * serviría hacia adelante y reintroduciría un campo derivado en el diff. No es un bug.
 *
 * @param areas mapa id→nombre, o `null` si todavía no se cargó (se distingue de "cargado y no
 *   está", que significa que el área se borró).
 */
export function formatCampoValor(
  campo: string,
  valor: unknown,
  areas: Record<string, string> | null,
): string {
  if (campo !== "area_id" || valor === null || valor === undefined || valor === "") {
    return formatValor(valor)
  }
  const id = String(valor)
  if (areas === null) return "Cargando…"
  // Área borrada: el id acortado es lo único cierto que queda. Ni el UUID entero (ilegible)
  // ni un guion (haría parecer que el campo estaba vacío, que es justo lo que no pasó).
  return areas[id] ?? `Área eliminada (${id.slice(0, 8)}…)`
}

/** Formatea un ISO datetime a "dd/mm/yyyy hh:mm". Si no parsea, devuelve el crudo. */
export function formatFechaHora(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/**
 * Texto compacto para la columna resumen. Muestra el cambio real (no un verbo genérico):
 *  - UPDATE con diff (ambos lados): 1 campo → "Etiqueta: antes → después"; varios → "N cambios".
 *  - Un solo lado (alta/baja/toggle/carga): 1 campo → "Etiqueta: valor"; varios → "N campos".
 */
export function resumenDiff(
  antes: Record<string, unknown> | null,
  nuevos: Record<string, unknown> | null,
): string {
  if (soloTraiaDerivados(antes, nuevos)) return SIN_CAMBIOS_AUDITADOS
  const visibles = new Set(clavesVisibles(antes, nuevos))
  const aKeys = antes ? Object.keys(antes).filter((k) => visibles.has(k)) : []
  const nKeys = nuevos ? Object.keys(nuevos).filter((k) => visibles.has(k)) : []
  if (aKeys.length && nKeys.length) {
    const keys = Array.from(new Set([...aKeys, ...nKeys]))
    if (keys.length === 1) {
      const k = keys[0]
      return `${campoLabel(k)}: ${formatValor(antes?.[k])} → ${formatValor(nuevos?.[k])}`
    }
    return `${keys.length} cambios`
  }
  const side = nKeys.length ? nuevos : antes
  const keys = nKeys.length ? nKeys : aKeys
  if (keys.length === 1 && side) return `${campoLabel(keys[0])}: ${formatValor(side[keys[0]])}`
  if (keys.length > 1) return `${keys.length} campos`
  return "—"
}
