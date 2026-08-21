import { antiguedad } from "@/components/features/empleados/ficha/_datosClave"
import type { Columna } from "@/components/ui/grillaTabla"
import type { EmpleadosFiltros } from "@/services/empleados"
import type { Empleado } from "@/types/empleado"

/**
 * La grilla de `/bajas`. Aparte de la tabla por lo mismo que `_grillaEmpleados`: es lo que el
 * encabezado, el esqueleto y las filas reales comparten para que las columnas no se muevan.
 *
 * 🔴 NO HAY COLUMNA DE ÁREA, y no es un olvido: el área de alguien que se fue es la que tenía el
 * día que se fue, y la fila la sigue mostrando aunque el área se haya reorganizado desde
 * entonces. Se puede FILTRAR por área (el backend lo hace en el WHERE, sobre el dato guardado)
 * pero mostrarla en la tabla de bajas invita a leerla como "el área que lo perdió", que para una
 * baja de hace tres años puede no existir más. El motivo y la antigüedad son las dos preguntas
 * que esta pantalla contesta.
 */
export const COLUMNAS: Columna[] = [
  { clave: "colaborador", label: "Colaborador", ancho: "" },
  { clave: "empresa", label: "Empresa", ancho: "w-[18%]" },
  { clave: "egreso", label: "Egreso", ancho: "w-[12%]" },
  { clave: "motivo", label: "Motivo", ancho: "w-[20%]" },
  { clave: "antiguedad", label: "Antigüedad", ancho: "w-[15%]" },
  // Solo el chevron a la ficha: la fila entera ya navega, esto es la señal de que se puede.
  { clave: "acciones", label: "", ancho: "w-[48px]" },
]

/**
 * Cuánto duró el vínculo, medido al día del egreso y no a hoy.
 *
 * Reusa la `antiguedad` de la ficha —la MISMA función con la que la barra de identidad calcula
 * la de alguien que sigue trabajando—, pasándole la fecha de egreso en lugar del default `hoy`.
 * Lo propio de esta pantalla son las dos guardas:
 *
 * 🔴 SIN `fecha_egreso` NO HAY ANTIGÜEDAD AL EGRESO. Medirla contra hoy sería inventar un número
 * que sigue creciendo todos los días para alguien que ya no está. Es el caso REAL de las bajas
 * que quedaron sin fecha, las mismas que el `NULLS FIRST` deja arriba de todo.
 *
 * 🔴 Y SI EL EGRESO ES ANTERIOR AL INGRESO tampoco: `antiguedad` interpreta una fecha posterior
 * a la de medición como "todavía no entró" y devuelve "Ingresa el 03/09/2027", que en una fila
 * de bajas no significa nada. Es dato roto, y una celda vacía lo dice mejor que una frase.
 */
export function antiguedadAlEgreso(emp: Pick<Empleado, "fecha_ingreso" | "fecha_egreso">): string {
  if (!emp.fecha_egreso || emp.fecha_egreso < emp.fecha_ingreso) return "—"
  return antiguedad(emp.fecha_ingreso, emp.fecha_egreso)
}

/**
 * El objeto de filtros con el que esta pantalla pide su listado. Hermano de
 * `filtrosProximosIngresos`, y por el mismo motivo: `estado` y `orden` son lo que DEFINE la
 * pantalla y no se ven en el render.
 *
 * 🔴 `orden: "fecha_egreso_desc"` = quién se fue último. Va al backend y no a un `.sort()` acá:
 * el listado pagina, y ordenar en el cliente ordenaría la página, no la lista. Su consecuencia
 * conocida —los nulos primero, porque postgrest no expresa `NULLS LAST`— está pineada con un
 * test del backend y NO se tapa reordenando acá.
 */
export function filtrosBajas(
  o: { search?: string; empresaId?: string; areaId?: string },
): EmpleadosFiltros {
  return {
    search: o.search || undefined,
    estado: "baja",
    orden: "fecha_egreso_desc",
    empresaId: o.empresaId,
    areaId: o.areaId || undefined,
  }
}
