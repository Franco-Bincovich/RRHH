import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla de `/usuarios`. Aparte de la tabla por lo mismo que `_grillaEmpleados` y `_bajas`: es
 * lo único que el encabezado, el esqueleto y las filas reales tienen que compartir para que las
 * columnas no se muevan entre un estado y el otro.
 *
 * 🔴 LA ÚNICA ACCIÓN DE FILA ES ELIMINAR, y NO se agregó un chevron a "la ficha del usuario"
 * porque esa pantalla NO EXISTE: no hay ruta `/usuarios/[id]` en el front ni `GET /{user_id}` en
 * el router. Un chevron a una ruta inexistente es peor que ninguno. (El propio router lo anota:
 * su `/exportar` está declarado antes de cualquier `/{...}` justamente por si algún día aparece.)
 */
export const COLUMNAS: Columna[] = [
  { clave: "nombre", label: "Nombre", ancho: "" },
  { clave: "apellido", label: "Apellido", ancho: "w-[16%]" },
  { clave: "email", label: "Email", ancho: "w-[24%]" },
  { clave: "username", label: "Usuario", ancho: "w-[15%]" },
  { clave: "rol", label: "Rol", ancho: "w-[16%]" },
  { clave: "acciones", label: "", ancho: "w-[64px] text-right" },
]
