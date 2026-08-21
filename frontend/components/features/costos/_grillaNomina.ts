import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla del "Detalle de nómina" de `/costos`. Aparte de la tabla por lo mismo que
 * `_grillaEmpleados` y `_bajas`: es lo único que el encabezado, el esqueleto y las filas reales
 * tienen que compartir para que las columnas no se muevan entre un estado y el otro.
 *
 * ⚠️ `ancho` LLEVA TAMBIÉN LA ALINEACIÓN de las columnas de plata: `Columna.ancho` es el
 * `className` del `<th>`, no un ancho literal. Poner el `text-right` acá es lo que hace que el
 * encabezado, el esqueleto y la fila real se alineen IGUAL — si viviera sólo en la celda de
 * datos, el título quedaría a la izquierda de sus propios números.
 *
 * ⚠️ La columna de acciones se filtra por `canWrite` en el consumidor: sin permiso no hay nada que
 * editar, y una columna vacía con su encabezado es una promesa que la pantalla no cumple.
 */
export const COLUMNAS_NOMINA: Columna[] = [
  { clave: "colaborador", label: "Colaborador", ancho: "" },
  { clave: "empresa", label: "Empresa", ancho: "w-[16%]" },
  { clave: "area", label: "Área", ancho: "w-[16%]" },
  { clave: "bruto", label: "Monto bruto", ancho: "w-[15%] text-right" },
  { clave: "neto", label: "Monto neto", ancho: "w-[15%] text-right" },
  { clave: "acciones", label: "", ancho: "w-[64px] text-right" },
]
