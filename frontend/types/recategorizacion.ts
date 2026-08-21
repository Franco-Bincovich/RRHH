/**
 * Recategorizaciones. Espejo de `backend/schemas/recategorizacion.py`.
 *
 * QUÉ ES. Capital Humano registra el cambio de rol, seniority o categoría de una persona. Carga
 * lo mínimo —colaborador, valores nuevos, motivo, impacto opcional— y el sistema completa el
 * resto. 🔴 **Registro puro: NO hay flujo de aprobación.** El sistema de diseño (§7) lo marca
 * como una de las seis cosas que un prototipo anterior prometió y no existen, así que la pantalla
 * no puede insinuarlo: no hay estado, ni "pendiente", ni botón de aprobar.
 *
 * 🔴 LOS `*_anterior` NO ENTRAN EN NINGÚN TIPO DE ENTRADA, y es la decisión central del módulo.
 * Los completa el BACKEND leyendo la última recategorización previa a `fecha_efectiva` (o, si no
 * hay ninguna, al empleado). Aceptarlos del cliente permitiría escribir un histórico que no
 * concuerda con el anterior, que es justo lo que la tabla existe para impedir. Por eso
 * `RecategorizacionCreate` no los tiene y el formulario no los pide: se MUESTRAN cuando vuelven.
 *
 * 🔴 NO HAY `deleteRecategorizacion` EN NINGÚN LADO. El backend no publica DELETE a propósito
 * (`recategorizaciones_escrituras.py`): borrar rompe la cadena de `*_anterior` que cuelga de cada
 * fila —la siguiente quedaría afirmando un valor anterior que ya no existe— y la auditoría ya
 * registra quién editó qué. Se puede EDITAR, no borrar.
 */

export interface Recategorizacion {
  id: string
  empleado_id: string
  empresa_id: string
  /** Cuándo RIGIÓ el cambio (puede ser retroactiva), no cuándo se cargó — eso es `created_at`. */
  fecha_efectiva: string
  rol_anterior: string | null
  rol_nuevo: string | null
  seniority_anterior: string | null
  seniority_nueva: string | null
  categoria_anterior: string | null
  categoria_nueva: string | null
  motivo: string
  /**
   * 🔴 ES UN MONTO EN PESOS, NO UN PORCENTAJE. §7 del sistema de diseño lo dice explícitamente:
   * "impacto porcentual" es una de las seis cosas que un prototipo prometió y no existen. La
   * pantalla nunca muestra un `%` acá.
   *
   * 🔴 Y ES `string`, NO `number`. El backend lo declara `Decimal` y **Pydantic serializa Decimal
   * a STRING en JSON** (verificado: `Decimal("150000.50")` → `"150000.50"`). Tiparlo `number`
   * compila igual y rompe en silencio: `"150000.50".toLocaleString()` devuelve el string tal cual,
   * así que el monto saldría sin separador de miles y nadie vería un error. Se parsea al formatear.
   *
   * ⚠️ `null` significa DOS cosas y no se distinguen a propósito: "no se cargó" o "no tenés
   * permiso de COSTOS". Un valor que dijera "oculto" confirmaría que hay un monto cargado, que es
   * la mitad del dato.
   */
  impacto_salarial: string | null
  registrado_por: string | null
  registrado_por_nombre: string | null
  empleado_nombre: string | null
  empresa_nombre: string | null
  created_at: string
  updated_at: string | null
}

/**
 * Alta. `empresa_id` NO viaja: lo deriva el backend DEL EMPLEADO (Vista vs Acción — el sidebar
 * decide qué se mira, la entidad padre decide de quién es la fila).
 *
 * ⚠️ Al menos uno de los tres valores nuevos tiene que venir cargado; si no, el backend responde
 * 422 `RECATEGORIZACION_SIN_CAMBIOS` (espejo del CHECK de la migración 117).
 */
export interface RecategorizacionCreate {
  empleado_id: string
  /** Ausente = hoy, lo pone el service. Editable hacia atrás. */
  fecha_efectiva?: string
  rol_nuevo?: string
  seniority_nueva?: string
  categoria_nueva?: string
  motivo: string
  impacto_salarial?: string
}

/**
 * Edición. Todo opcional.
 *
 * 🔴 `empleado_id` NO ESTÁ, y no es un olvido del tipo: el backend tampoco lo acepta. Mover una
 * recategorización de persona invalidaría los `*_anterior` de las dos cadenas —la que deja y la
 * que integra— sin ninguna señal. Si se cargó sobre quien no era, se corrige el motivo y se
 * registra la buena. El formulario de edición deshabilita el selector por eso.
 */
export type RecategorizacionUpdate = Omit<Partial<RecategorizacionCreate>, "empleado_id">

export interface RecategorizacionListResponse {
  items: Recategorizacion[]
  /** 🔴 El total REAL del filtro (`count="exact"`), no `items.length`. Es lo que cuenta el pie. */
  total: number
  page: number
  page_size: number
  total_pages: number
}
