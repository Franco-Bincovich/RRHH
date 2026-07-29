import type { Empleado, EmpleadoCreate } from "@/types/empleado"
import type { FormData, FormErrors } from "./_constants"

/** Validación pura del form. Devuelve el mapa de errores (vacío = válido). */
export function validate(form: FormData, isEdit: boolean): FormErrors {
  const errors: FormErrors = {}
  if (!isEdit && !form.empresa_id) errors.empresa_id = "La empresa es requerida"
  if (!form.nombre.trim()) errors.nombre = "El nombre es requerido"
  if (!form.apellido.trim()) errors.apellido = "El apellido es requerido"
  if (!form.email_corporativo.trim()) {
    errors.email_corporativo = "El email es requerido"
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email_corporativo)) {
    errors.email_corporativo = "El email no es válido"
  }
  if (!form.area_id) errors.area_id = "El área es requerida"
  if (form.roles.length === 0) errors.roles = "Agregá al menos un rol"
  if (!form.fecha_ingreso) errors.fecha_ingreso = "La fecha de ingreso es requerida"
  if (form.horas_contrato.trim() && !/^\d+$/.test(form.horas_contrato.trim())) {
    errors.horas_contrato = "Las horas tienen que ser un número entero"
  }
  return errors
}

/** Mapea un Empleado existente al estado del form (modo edición). */
export function toFormData(empleado: Empleado): FormData {
  return {
    empresa_id: "",
    nombre: empleado.nombre,
    apellido: empleado.apellido,
    email_corporativo: empleado.email_corporativo,
    area_id: empleado.area_id,
    roles: empleado.roles ?? [],
    modalidad_trabajo: empleado.modalidad_trabajo,
    tipo_contrato: empleado.tipo_contrato,
    fecha_ingreso: empleado.fecha_ingreso,
    telefono: empleado.telefono ?? "",
    fecha_nacimiento: empleado.fecha_nacimiento ?? "",
    dni: empleado.dni ?? "",
    cuil: empleado.cuil ?? "",
    legajo: empleado.legajo ?? "",
    manager_id: empleado.manager_id ?? "",
    dias_vacaciones_asignados: String(empleado.dias_vacaciones_asignados ?? 14),
    tipo_documento: empleado.tipo_documento ?? "",
    sexo: empleado.sexo ?? "",
    telefono_alternativo: empleado.telefono_alternativo ?? "",
    email_personal: empleado.email_personal ?? "",
    domicilio: empleado.domicilio ?? "",
    domicilio_calle: empleado.domicilio_calle ?? "",
    domicilio_numero: empleado.domicilio_numero ?? "",
    domicilio_piso_depto: empleado.domicilio_piso_depto ?? "",
    domicilio_localidad: empleado.domicilio_localidad ?? "",
    domicilio_provincia: empleado.domicilio_provincia ?? "",
    domicilio_cp: empleado.domicilio_cp ?? "",
    estudios: empleado.estudios ?? "",
    ubicacion: empleado.ubicacion ?? "",
    turno: empleado.turno ?? "",
    horas_contrato: empleado.horas_contrato != null ? String(empleado.horas_contrato) : "",
    organismo: empleado.organismo ?? "",
    gerencia: empleado.gerencia ?? "",
    sector: empleado.sector ?? "",
    seniority: empleado.seniority ?? "",
    perfil: empleado.perfil ?? "",
    categoria: empleado.categoria ?? "",
    referido: empleado.referido ?? "",
    es_lider: empleado.es_lider ?? false,
  }
}

/** Arma el payload de la API a partir del form (sin empresa_id; lo agrega el create). */
export function buildPayload(form: FormData): Omit<EmpleadoCreate, "empresa_id"> {
  return {
    nombre: form.nombre,
    apellido: form.apellido,
    email_corporativo: form.email_corporativo,
    area_id: form.area_id,
    roles: form.roles,
    modalidad_trabajo: form.modalidad_trabajo,
    tipo_contrato: form.tipo_contrato,
    fecha_ingreso: form.fecha_ingreso,
    telefono: form.telefono || undefined,
    fecha_nacimiento: form.fecha_nacimiento || undefined,
    dni: form.dni || undefined,
    cuil: form.cuil || undefined,
    legajo: form.legajo || undefined,
    manager_id: form.manager_id || null,  // null explícito = "Sin superior" (limpiar); undefined = no tocar
    dias_vacaciones_asignados: form.dias_vacaciones_asignados
      ? parseInt(form.dias_vacaciones_asignados, 10)
      : undefined,
    tipo_documento: form.tipo_documento || undefined,
    sexo: form.sexo || undefined,
    telefono_alternativo: form.telefono_alternativo || undefined,
    email_personal: form.email_personal || undefined,
    domicilio: form.domicilio || undefined,
    domicilio_calle: form.domicilio_calle || undefined,
    domicilio_numero: form.domicilio_numero || undefined,
    domicilio_piso_depto: form.domicilio_piso_depto || undefined,
    domicilio_localidad: form.domicilio_localidad || undefined,
    domicilio_provincia: form.domicilio_provincia || undefined,
    domicilio_cp: form.domicilio_cp || undefined,
    estudios: form.estudios || undefined,
    ubicacion: form.ubicacion || undefined,
    turno: form.turno || undefined,
    horas_contrato: form.horas_contrato ? parseInt(form.horas_contrato, 10) : undefined,
    organismo: form.organismo || undefined,
    gerencia: form.gerencia || undefined,
    sector: form.sector || undefined,
    seniority: form.seniority || undefined,
    perfil: form.perfil || undefined,
    categoria: form.categoria || undefined,
    referido: form.referido || undefined,
    es_lider: form.es_lider,
  }
}
