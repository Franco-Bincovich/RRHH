import { createArea, updateArea } from "@/services/areas"
import { validate, type FormData, type FormErrors } from "@/components/features/areas/areaForm"
import type { Area, AreaCreate } from "@/types/area"

/**
 * La decisión de guardar un área: validar primero y mandar SOLO si pasa.
 *
 * 🔴 POR QUÉ VIVE ACÁ Y NO EN EL CUERPO DE `AreaModal`. El modal usa `Dialog` de Radix, que
 * monta por PORTAL: con vitest sin jsdom, `renderToStaticMarkup(<AreaModal/>)` devuelve "". Un
 * test de ese componente pasaría con el formulario entero borrado, así que la decisión que hay
 * que poder desmentir tiene que ser una función suelta. Molde exacto: `guardarCliente.ts`.
 *
 * 🔴 Y ES LA ÚNICA PUERTA A `createArea`/`updateArea` DESDE ESTA PANTALLA. Que el modal no los
 * importe es lo que hace que el test de acá hable del comportamiento real y no de un helper
 * paralelo: si el modal pudiera llamar a los services por su cuenta, este archivo sería una
 * opinión sobre lo que el modal debería hacer. Hay un test estructural que lo verifica.
 *
 * EL BUG QUE CIERRA: el modal armaba `empresa_id: empresaId ?? getEmpresaActivaId() ?? ""` sin
 * validar nada. Con el sidebar en "Todas las empresas" —el default— eso mandaba `""`, y como
 * `AreaCreate.empresa_id` era `str` en el backend, Pydantic lo aceptaba y el `""` moría en
 * Postgres con `22P02` como **500**. Hoy el tipo es `UUID` (sale 422) y acá el `""` ni sale.
 */
export async function guardarArea(
  form: FormData, area?: Area,
): Promise<FormErrors | null> {
  const errores = validate(form, Boolean(area))
  if (Object.keys(errores).length > 0) return errores

  if (area) {
    await updateArea(area.id, {
      nombre: form.nombre.trim(),
      descripcion: form.descripcion.trim() || undefined,
      responsable_id: form.responsable_id || undefined,
    })
  } else {
    // Sin `?? ""`: `form.empresa_id` ya pasó la validación, así que sólo puede ser un UUID.
    const payload: AreaCreate = {
      empresa_id: form.empresa_id,
      nombre: form.nombre.trim(),
      descripcion: form.descripcion.trim() || undefined,
      responsable_id: form.responsable_id || undefined,
    }
    await createArea(payload)
  }
  return null
}
