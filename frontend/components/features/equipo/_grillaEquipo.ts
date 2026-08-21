import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla de `/equipo`. Aparte de la tabla por lo mismo que `_grillaEmpleados` y `_bajas`: es lo
 * único que el encabezado, el esqueleto y las filas reales tienen que compartir para que las
 * columnas no se muevan entre un estado y el otro.
 *
 * 🔴 NO HAY COLUMNA DE ACCIONES, y no es un olvido. El único destino natural de una fila sería la
 * ficha del legajo (`/empleados/{id}`), y **el rol que usa esta pantalla no puede entrar ahí**:
 * `mandos_medios` tiene VACACIONES y AUSENCIAS, no EMPLEADOS (`utils/permisos.py`), y el
 * `AuthGuard` lo rebota. Un chevron que lleva a una pantalla prohibida es peor que no tener
 * ninguno: ofrece algo que no se puede hacer y no dice por qué. El día que exista un destino
 * permitido —la vacación de esa persona, por ejemplo— la columna entra acá.
 *
 * ⚠️ La columna Empresa se muestra SIEMPRE, al revés que en las otras tablas del bloque: acá el
 * ownership cuelga del `manager_id` y **un empleado puede tener superior de otra empresa del
 * grupo** (`services/_alcance_mandos.py`, la única excepción declarada a la barrera de empresa).
 * O sea que este listado puede mezclar sociedades aunque el sidebar tenga una elegida, y sin la
 * columna no habría forma de notarlo.
 */
export const COLUMNAS: Columna[] = [
  { clave: "apellido", label: "Apellido", ancho: "" },
  { clave: "nombre", label: "Nombre", ancho: "w-[30%]" },
  { clave: "empresa", label: "Empresa", ancho: "w-[30%]" },
]
