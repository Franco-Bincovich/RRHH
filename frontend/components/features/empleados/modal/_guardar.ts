import { createEmpleado, updateEmpleado } from "@/services/empleados"
import type { Empleado } from "@/types/empleado"

import type { FormData } from "./_constants"
import { buildPayload } from "./form-utils"

/**
 * El envío: crear o actualizar. Salió de `useEmpleadoForm` para que el hook quedara adentro del
 * límite de 80, y el corte es el natural — acá está la única diferencia real entre los dos modos
 * del modal.
 *
 * 🔴 `estado` VIAJA SOLO EN EL ALTA, y es la mitad de la regla de A3 que se ve desde el front (la
 * otra es que el campo no se renderiza en edición). El pase `preingreso` → `activo` es el endpoint
 * `/activar`, que verifica que la fecha de ingreso ya haya ocurrido; si el estado viajara en el
 * PUT, esa guarda se saltearía con una edición cualquiera del legajo.
 */
export function guardarEmpleado(form: FormData, empleado: Empleado | undefined): Promise<unknown> {
  const base = buildPayload(form)
  return empleado
    ? updateEmpleado(empleado.id, base)
    : createEmpleado({ ...base, empresa_id: form.empresa_id, estado: form.estado })
}
