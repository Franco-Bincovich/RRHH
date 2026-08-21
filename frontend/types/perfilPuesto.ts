/**
 * El catálogo de perfiles de puesto. Espejo de `backend/schemas/perfil_puesto.py`.
 *
 * 🔴 UN PERFIL ES DEL GRUPO: NO TIENE `empresa_id` NI `area_id`, y las dos ausencias son la
 * decisión de fondo, no un olvido del tipo. Ninguna ruta del backend lee `X-Empresa-Id`, así que
 * el selector del sidebar NO acota esta pantalla — es lo contrario a lo que hace todo el resto
 * del sistema, y por eso la pantalla lo dice en voz alta en vez de dejarlo escrito acá.
 *
 * 🔴 LO QUE UN PERFIL **NO** TIENE, copiado del backend para que no se vuelva a proponer desde
 * este lado: **competencias**, **ubicación** y **contador de ocupantes o de vacantes**. Las tres
 * las inventó un prototipo y no están en el modelo (§7 del sistema de diseño). No se agregan ni
 * como `0`: un contador en cero se lee como "este perfil no tiene vacantes", que es una
 * afirmación que el sistema no puede hacer.
 */

/** Los tres vocabularios cerrados. Copia de los `Literal` del backend, que a su vez copian los
 *  CHECK de la migración 113. Un valor fuera de la lista sale como 422 con el nombre del campo.
 *  ⚠️ Las ETIQUETAS legibles NO están acá: las sirve `GET /api/perfiles-puesto/campos`. */
export type ModalidadPerfil = "presencial" | "remoto" | "hibrido"
export type TipoContratoPerfil = "efectivo" | "plazo_fijo" | "contratado" | "pasantia"
export type NivelPerfil =
  | "junior" | "semi_senior" | "senior" | "lider" | "manager" | "director" | "c_level"

/** Los 12 campos editables, en el mismo orden en que se llenan. Ver `PerfilPuestoBase`. */
export interface PerfilPuestoBase {
  nombre: string
  descripcion: string | null
  funciones: string | null
  experiencia: string | null
  formacion: string | null
  conocimientos_tecnicos: string | null
  requisitos: string | null
  ofrecemos: string | null
  modalidad: ModalidadPerfil | null
  tipo_contrato: TipoContratoPerfil | null
  nivel: NivelPerfil | null
  jornada: string | null
}

export interface PerfilPuesto extends PerfilPuestoBase {
  id: string
  /** La baja es LÓGICA. `false` = dado de baja: sale de los selects y se puede reactivar. */
  activo: boolean
  created_by: string | null
  created_at: string
  updated_at: string | null
}

/** Alta. `created_by` NO viaja en el body: lo pone el backend con el usuario autenticado. */
export type PerfilPuestoCreate = { nombre: string } & Partial<Omit<PerfilPuestoBase, "nombre">>

/**
 * Edición parcial.
 *
 * ⚠️ CONSECUENCIA ASUMIDA, la misma que documenta `PerfilPuestoUpdate` del backend: el service
 * arma el patch con `exclude_none`, así que **`null` no vacía un campo**. Para borrar el
 * contenido de un campo de texto se manda la cadena vacía (`""`), que sí viaja y sí se escribe.
 * Por eso el formulario manda `""` y nunca `null` en los campos de texto.
 */
export type PerfilPuestoUpdate = Partial<PerfilPuestoBase> & { activo?: boolean }

export interface PerfilPuestoListResponse {
  items: PerfilPuesto[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/* ── Lo que devuelve GET /api/perfiles-puesto/campos ──────────────────────────
 *
 * 🔴 ESTE ES EL CONTRATO QUE HACE QUE EL FORMULARIO NO SE ESCRIBA DOS VECES.
 * Los labels, los textos de ayuda y los tres vocabularios viven en el backend
 * (`schemas/_perfil_puesto_campos.py`) y se sirven por endpoint. El formulario se construye
 * RECORRIENDO `campos`, no contra una lista escrita acá: si alguien agrega un campo en el
 * backend, la pantalla lo muestra sin tocar el front. Mismo criterio que el endpoint de
 * provincias, y acá además es obligatorio — los `value` de los vocabularios son TAMBIÉN los
 * `Literal` con los que valida Pydantic, así que una copia del front que derive ofrecería en un
 * select un valor que el backend rechaza con 422.
 */

/** El control con el que se edita un campo. `tipo` lo decide el backend. */
export interface CampoPerfil {
  campo: string
  label: string
  ayuda: string
  tipo: "texto" | "textarea" | "select"
}

/** Un valor de un vocabulario cerrado con su etiqueta legible. */
export interface OpcionPerfil {
  value: string
  label: string
}

export interface CamposPerfilResponse {
  /** EN EL ORDEN EN QUE SE LLENAN. `requisitos` va cuarto del bloque y no primero, a propósito. */
  campos: CampoPerfil[]
  /**
   * 🔴 VA ARRIBA DEL BLOQUE, NO EN UN TOOLTIP, y el backend lo declara así: un tooltip se lee
   * después de haber escrito. Sin esta nota, Capital Humano pega el bloque "Requisitos" entero
   * del aviso dentro de `requisitos` y deja vacíos los tres campos específicos — y ahí el perfil
   * deja de servir para filtrar y para armar un aviso por partes.
   */
  nota_requisitos: string
  modalidades: OpcionPerfil[]
  tipos_contrato: OpcionPerfil[]
  niveles: OpcionPerfil[]
}
