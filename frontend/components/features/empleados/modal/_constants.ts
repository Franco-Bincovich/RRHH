import type { ChangeEvent } from "react"

export type FormData = {
  empresa_id: string
  nombre: string
  apellido: string
  email_corporativo: string
  area_id: string
  roles: string[]
  modalidad_trabajo: string
  tipo_contrato: string
  fecha_ingreso: string
  telefono: string
  fecha_nacimiento: string
  dni: string
  cuil: string
  legajo: string
  manager_id: string
  dias_vacaciones_asignados: string
  // Legajo ampliado (A1.3b)
  tipo_documento: string
  sexo: string
  telefono_alternativo: string
  email_personal: string
  domicilio: string
  domicilio_calle: string
  domicilio_numero: string
  domicilio_piso_depto: string
  domicilio_localidad: string
  domicilio_provincia: string
  domicilio_cp: string
  estudios: string
  ubicacion: string
  turno: string
  horas_contrato: string
  organismo: string
  gerencia: string
  sector: string
  seniority: string
  perfil: string
  categoria: string
  referido: string
  es_lider: boolean
}

export type FormErrors = Partial<Record<keyof FormData, string>>

/** Claves de campos de texto (string). Excluye roles (lista) y es_lider (booleano). */
export type TextKey = Exclude<keyof FormData, "roles" | "es_lider">
/** Claves con autocompletado de texto libre + sugerencias (single-value). */
export type AutocompleteKey =
  | "tipo_documento" | "ubicacion" | "organismo" | "gerencia" | "sector"
  | "seniority" | "perfil" | "categoria"

/** Handler de cambio de un input/select controlado del form. */
export type FieldChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void
/** Fábrica de handlers por campo de texto (el orquestador es dueño del estado). */
export type FieldFactory = (key: TextKey) => FieldChange

export type TextField = {
  field: TextKey
  label: string
  required?: boolean
  type?: string
  placeholder?: string
}

export const EMPTY: FormData = {
  empresa_id: "",
  nombre: "",
  apellido: "",
  email_corporativo: "",
  area_id: "",
  roles: [],
  modalidad_trabajo: "presencial",
  tipo_contrato: "Relación de dependencia",
  fecha_ingreso: "",
  telefono: "",
  fecha_nacimiento: "",
  dni: "",
  cuil: "",
  legajo: "",
  manager_id: "",
  dias_vacaciones_asignados: "14",
  tipo_documento: "",
  sexo: "",
  telefono_alternativo: "",
  email_personal: "",
  domicilio: "",
  domicilio_calle: "",
  domicilio_numero: "",
  domicilio_piso_depto: "",
  domicilio_localidad: "",
  domicilio_provincia: "",
  domicilio_cp: "",
  estudios: "",
  ubicacion: "",
  turno: "",
  horas_contrato: "",
  organismo: "",
  gerencia: "",
  sector: "",
  seniority: "",
  perfil: "",
  categoria: "",
  referido: "",
  es_lider: false,
}

// Personal, en orden: identidad → documento (tipo + número + CUIT/CUIL) → resto.
export const PERSONAL_IDENTITY_FIELDS: TextField[] = [
  { field: "nombre", label: "Nombre", required: true },
  { field: "apellido", label: "Apellido", required: true },
]

// Documento: van JUNTO al autocompletado tipo_documento (tipo + número).
export const PERSONAL_DOC_FIELDS: TextField[] = [
  { field: "dni", label: "Documento" },
  { field: "cuil", label: "CUIT/CUIL" },
]

export const PERSONAL_CONTACT_FIELDS: TextField[] = [
  { field: "legajo", label: "Legajo" },
  { field: "fecha_nacimiento", label: "Fecha de nacimiento", type: "date" },
  { field: "telefono", label: "Teléfono", type: "tel" },
  { field: "telefono_alternativo", label: "Teléfono alternativo", type: "tel" },
  { field: "email_corporativo", label: "Email corporativo", required: true, type: "email" },
  { field: "email_personal", label: "Email alternativo", type: "email" },
  { field: "estudios", label: "Estudios" },
]

/**
 * Domicilio desglosado (C4). Va en su propio bloque y NO junto al resto de los datos de
 * contacto: son seis campos que se completan de una sola vez, y mezclarlos con teléfono y
 * email hace que el formulario se lea como una lista sin fin.
 *
 * `domicilio_provincia` NO está acá: es un select cerrado y lo renderiza DomicilioFields.
 * `domicilio` (el texto libre viejo) tampoco: dejó de editarse, se muestra como referencia en
 * la ficha mientras estos estén vacíos.
 */
export const DOMICILIO_FIELDS: TextField[] = [
  { field: "domicilio_calle", label: "Calle" },
  { field: "domicilio_numero", label: "Número", placeholder: "Ej: 1234, S/N, KM 4" },
  { field: "domicilio_piso_depto", label: "Piso / Depto" },
  { field: "domicilio_localidad", label: "Localidad" },
  { field: "domicilio_cp", label: "Código postal" },
]

export const LABORAL_TEXT_FIELDS: TextField[] = [
  { field: "turno", label: "Turno", placeholder: "Ej: 8 a 17 hs" },
  { field: "horas_contrato", label: "Horas por día", type: "number" },
  { field: "fecha_ingreso", label: "Fecha de ingreso", required: true, type: "date" },
  { field: "referido", label: "Referido" },
  { field: "dias_vacaciones_asignados", label: "Días de vacaciones asignados", type: "number" },
]

export const PERSONAL_AUTOCOMPLETE: ReadonlyArray<{ field: AutocompleteKey; label: string }> = [
  { field: "tipo_documento", label: "Tipo de documento" },
]

export const LABORAL_AUTOCOMPLETE: ReadonlyArray<{ field: AutocompleteKey; label: string }> = [
  { field: "ubicacion", label: "Ubicación" },
  { field: "organismo", label: "Organismo" },
  { field: "gerencia", label: "Gerencia" },
  { field: "sector", label: "Sector" },
  { field: "seniority", label: "Seniority" },
  { field: "perfil", label: "Perfil" },
  { field: "categoria", label: "Categoría" },
]

export const SELECT_CLASS =
  "h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
