import type { ChangeEvent } from "react"

import type { EstadoAlta } from "@/types/empleado"


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
  /** Estado de ALTA. Solo se usa al crear; en edición el campo ni se renderiza. */
  estado: EstadoAlta
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
  seniority: string
  categoria: string
  referido: string
  es_lider: boolean
}

export type FormErrors = Partial<Record<keyof FormData, string>>

/** Claves de campos de texto (string). Excluye roles (lista), es_lider (booleano) y estado
 *  (unión cerrada: su control es un select propio, no un input de texto). */
export type TextKey = Exclude<keyof FormData, "roles" | "es_lider" | "estado">
/**
 * Claves con autocompletado de texto libre + sugerencias (single-value).
 *
 * 🔴 ERAN OCHO HASTA EL 25/8/2026: salieron las CUATRO del bloque N2. `organismo`, `sector` y
 * `perfil` porque están en CERO filas; `gerencia` por otra razón, y por eso NO se puede leer como
 * "las cuatro estaban vacías": tiene 31 de 41 y **dejó de ser un campo del legajo para ser la
 * agrupación del organigrama por proyecto**, alimentada sólo por el archivo de nómina. Editarla a
 * mano no movía a nadie en el organigrama (ver `db/schema.sql` y `_nomina_proyectos.py`), o sea
 * que era un campo que parecía editable y cuya edición no hacía nada. Las COLUMNAS no se tocaron:
 * es DDL. El backend recortó `CAMPOS_AUTOCOMPLETABLES` en paralelo, así que pedirlas da 400.
 */
export type AutocompleteKey =
  | "tipo_documento" | "ubicacion" | "seniority" | "categoria"

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
  estado: "activo",
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
  seniority: "",
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
 * Domicilio desglosado (C4). Va en su propio bloque y NO junto al resto de los datos de contacto:
 * son seis campos que se completan de una vez, y mezclarlos con teléfono y email hace que el
 * formulario se lea como una lista sin fin.
 *
 * `domicilio_provincia` NO está acá: es un select cerrado y lo renderiza DomicilioFields.
 * `domicilio` (el texto libre viejo) tampoco: dejó de editarse, se muestra en la ficha como
 * referencia mientras estos estén vacíos.
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
  // Vacío = lo calcula el backend del turno, y el placeholder lo dice: un campo que se completa
  // solo DESPUÉS de guardar se lee como un campo que no se guardó.
  { field: "horas_contrato", label: "Horas por día", type: "number", placeholder: "Se calcula del turno" },
  { field: "fecha_ingreso", label: "Fecha de ingreso", required: true, type: "date" },
  { field: "referido", label: "Referido" },
  { field: "dias_vacaciones_asignados", label: "Días de vacaciones asignados", type: "number" },
]

export const PERSONAL_AUTOCOMPLETE: ReadonlyArray<{ field: AutocompleteKey; label: string }> = [
  { field: "tipo_documento", label: "Tipo de documento" },
]

/**
 * Los tres campos del legajo que se completan escribiendo, con sugerencias de lo ya cargado.
 * 🔴 `seniority` MOTIVÓ EL BLOQUE N3. La columna tiene TRES escritores —este formulario, el import
 * de nómina y la recategorización— y cada uno escribía su grafía: producción tenía `senior` (5) y
 * `SENIOR` (1) como dos valores, y "Distribución de plantilla" partía en dos a los 6 seniors. El
 * combobox ya sugería lo existente; faltaba **normalizar al guardar**, y eso se cerró en el
 * backend (`schemas/_legajo_normalizado`), el único punto por el que pasan los tres. `categoria`
 * es el nivel dentro del seniority y **acepta números pelados** ("3" es real): texto libre.
 */
export const LABORAL_AUTOCOMPLETE: ReadonlyArray<{ field: AutocompleteKey; label: string }> = [
  { field: "ubicacion", label: "Ubicación" },
  { field: "seniority", label: "Seniority" },
  { field: "categoria", label: "Categoría" },
]

/*
 * La clase del `<input list="tipo_contrato_opciones">` de `DatosLaboralesFields`, y de nada más.
 *
 * 🔴 SE LLAMABA `SELECT_CLASS` Y EL NOMBRE PASÓ A MENTIR. Vestía los 8 `<select>` del modal de
 * empleado además de este input; el 19/8/2026 esos selects pasaron a `components/ui/select.tsx` y
 * quedó un solo consumidor, que no es un select. Un nombre que describe lo que la constante YA NO
 * hace es peor que no tener nombre: el próximo que la lea va a buscar el select que la usa.
 *
 * ⚠️ Candidato a desaparecer: el valor es casi el de `components/ui/input.tsx`, así que el campo
 * podría ser `<Input list="tipo_contrato_opciones" />` y esta constante irse con él. No se hizo
 * en la tanda de selects para no meter inputs en el medio.
 */
export const INPUT_DATALIST_CLASS =
  "h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
