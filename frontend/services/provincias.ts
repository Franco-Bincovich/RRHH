import { apiFetch } from "@/services/api"

/**
 * Las 24 jurisdicciones argentinas para el select de domicilio.
 *
 * 🔴 SE PIDEN AL BACKEND EN VEZ DE TENERLAS ACÁ, y son 24 strings que no cambian desde 1990.
 * El motivo no es el tamaño: es que el backend VALIDA contra su propia lista
 * (backend/schemas/_provincias.py) y devuelve 422 si el valor no está. Con una copia local,
 * el día que las dos se separen el usuario elegiría del select una opción que el backend
 * rechaza — un formulario que se ve bien y no se puede guardar. Es el mismo problema que
 * `permisos.ts` como espejo manual de `permisos.py`, que ya está anotado como deuda.
 */
export async function fetchProvincias(): Promise<string[]> {
  return apiFetch<string[]>("/api/empleados/provincias")
}
