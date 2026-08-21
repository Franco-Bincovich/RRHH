import type { Columna } from "@/components/ui/grillaTabla"
import type { EmpleadosFiltros } from "@/services/empleados"

/**
 * La grilla de `/proximos-ingresos` y la cuenta regresiva de cada fila.
 *
 * Aparte de la tabla por lo mismo que `_grillaEmpleados`: acá está lo que el encabezado, el
 * esqueleto y las filas reales tienen que compartir para que las columnas no se muevan entre un
 * estado y el otro. `textoFaltan` vive acá y no en el componente porque es una decisión de
 * producto —cómo se dice "faltan N días"— y así se puede probar sin renderizar nada.
 */
export const COLUMNAS: Columna[] = [
  { clave: "colaborador", label: "Colaborador", ancho: "" },
  { clave: "empresa", label: "Empresa", ancho: "w-[18%]" },
  { clave: "area", label: "Área", ancho: "w-[16%]" },
  { clave: "ingreso", label: "Ingresa", ancho: "w-[12%]" },
  { clave: "faltan", label: "Faltan", ancho: "w-[13%]" },
  // Acá el encabezado SÍ va vacío pero la columna es ancha: lleva un botón con texto
  // ("Confirmar ingreso"), no un ícono. El nombre accesible lo pone `Encabezado`.
  { clave: "acciones", label: "", ancho: "w-[180px]" },
]

/**
 * Cómo se dice la cuenta regresiva de un ingreso.
 *
 * 🔴 `destacado` MARCA LO QUE YA TENDRÍA QUE HABER PASADO, no lo que está por pasar. Un ingreso
 * de dentro de dos semanas no pide nada de nadie; uno cuya fecha ya llegó y sigue en
 * `preingreso` es exactamente la fila sobre la que hay que apretar "Confirmar ingreso" — y es la
 * única que el backend deja activar. Pintar de warning "en 14 días" enseñaría a ignorar el color.
 *
 * ⚠️ "Hoy", "Mañana" y "Ayer" en palabras, no "en 0 días" / "en 1 días". Es el caso más frecuente
 * de la pantalla (el día del ingreso es cuando alguien la abre) y "en 0 días" se lee como un bug.
 *
 * @param dias lo que devuelve `diasHasta`: negativo = ya pasó, 0 = hoy, `null` = fecha ilegible.
 */
export function textoFaltan(dias: number | null): { texto: string; destacado: boolean } {
  if (dias === null) return { texto: "—", destacado: false }
  if (dias === 0) return { texto: "Hoy", destacado: true }
  if (dias === 1) return { texto: "Mañana", destacado: false }
  if (dias === -1) return { texto: "Ayer", destacado: true }
  if (dias < 0) return { texto: `Hace ${-dias} días`, destacado: true }
  return { texto: `En ${dias} días`, destacado: false }
}

/**
 * El objeto de filtros con el que esta pantalla pide su listado.
 *
 * 🔴 ES UNA FUNCIÓN PURA Y NO UN `useMemo` ADENTRO DE LA PÁGINA porque acá viven las DOS
 * constantes que definen la pantalla, y las dos son invisibles mirando el render:
 *
 *   · `estado: "preingreso"` — sin él el listado ni siquiera los traería: el default del backend
 *     los EXCLUYE a propósito (`_empleado_row.filtro_estado`), que es lo que mantiene
 *     /empleados mostrando gente que ya entró.
 *   · `orden: "fecha_ingreso_asc"` — la pregunta que trae acá es "quién entra primero", no "cómo
 *     se apellida". Va al backend, NUNCA como `.sort()` en la tabla: el listado pagina, así que
 *     ordenar en el cliente ordenaría LA PÁGINA — con 40 preingresos la primera saldría prolija
 *     y no sería la de los que entran antes.
 *
 * Sacándolas de la página se pueden afirmar sin renderizar nada, que es lo único que vitest
 * puede hacer sin jsdom. Adentro de un `useMemo` el único test posible sería leer el texto del
 * archivo.
 */
export function filtrosProximosIngresos(
  o: { search?: string; empresaId?: string; areaId?: string },
): EmpleadosFiltros {
  return {
    search: o.search || undefined,
    estado: "preingreso",
    orden: "fecha_ingreso_asc",
    empresaId: o.empresaId,
    areaId: o.areaId || undefined,
  }
}
