import { useEffect, useState } from "react"

import type { Empleado } from "@/types/empleado"

import { EMPTY, type AutocompleteKey, type FormData, type FormErrors, type TextKey } from "./_constants"
import { guardarEmpleado } from "./_guardar"
import { estadoSegunFecha, toFormData, validate } from "./form-utils"
import { avisarGuardado } from "@/components/features/shared/avisoGuardado"

/**
 * El ESTADO del formulario de empleado: valores, errores, envío y los handlers por campo.
 *
 * Salió de `EmpleadoModal.tsx` al aplicarle el patrón de modal de formulario (§3): el modal
 * quedaba en 189 líneas contra el límite de 150, y el corte por responsabilidad es éste — el
 * componente se queda con el JSX del patrón (encabezado con la consecuencia, banner, aviso de
 * impacto, pie) y el hook con lo que ese JSX muestra. Ninguna de las dos mitades necesita leer
 * a la otra.
 */
export function useEmpleadoForm(open: boolean, empleado: Empleado | undefined, onSuccess: () => void) {
  const isEdit = Boolean(empleado)
  const [form, setForm] = useState<FormData>(EMPTY)
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")
  /** El default de estado se pierde en cuanto el usuario elige. El porqué, en `estadoSegunFecha`. */
  const [estadoTocado, setEstadoTocado] = useState(false)

  // Resetear formulario al abrir/cerrar
  useEffect(() => {
    setForm(empleado ? toFormData(empleado) : EMPTY)
    setErrors({})
    setServerError("")
    setEstadoTocado(false)
  }, [empleado, open])

  // Setter único: actualiza un campo y limpia su error. El orquestador es el dueño del estado.
  function setField<K extends keyof FormData>(key: K, value: FormData[K]) {
    setForm((prev) => {
      const siguiente = { ...prev, [key]: value }
      // La fecha de ingreso arrastra el estado de alta mientras el usuario no lo haya elegido.
      if (key === "fecha_ingreso" && !estadoTocado) siguiente.estado = estadoSegunFecha(String(value))
      return siguiente
    })
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  function handleEmpresaChange(e: React.ChangeEvent<HTMLSelectElement>) {
    // Resetear área al cambiar empresa para evitar incoherencias
    setForm((prev) => ({ ...prev, empresa_id: e.target.value, area_id: "" }))
    setErrors((prev) => ({ ...prev, empresa_id: undefined, area_id: undefined }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate(form, isEdit)
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setSubmitting(true); setServerError("")
    try {
      await guardarEmpleado(form, empleado)
      avisarGuardado("Colaborador", "m", isEdit)
      onSuccess()
    } catch {
      setServerError("No se pudo guardar. Probá de nuevo; si vuelve a pasar, avisale a sistemas.")
    } finally {
      setSubmitting(false)
    }
  }

  return {
    isEdit, form, errors, submitting, serverError, setField, handleEmpresaChange, handleSubmit,
    /** La cuenta del banner de resumen. Un `undefined` en el mapa NO es un error. */
    cantidadErrores: Object.values(errors).filter(Boolean).length,
    field: (key: TextKey) =>
      (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setField(key, e.target.value),
    onValue: (key: AutocompleteKey) => (value: string) => setField(key, value),
    onEstadoAlta: (value: FormData["estado"]) => { setEstadoTocado(true); setField("estado", value) },
    onLider: (value: boolean) => setField("es_lider", value),
    onRoles: (roles: string[]) => setField("roles", roles),
  }
}
