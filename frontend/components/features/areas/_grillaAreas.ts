import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla de `/areas`. Aparte de la tabla por lo mismo que `_grillaEmpleados` y `_bajas`: es lo
 * único que el encabezado, el esqueleto y las filas reales tienen que compartir para que las
 * columnas no se muevan entre un estado y el otro.
 *
 * 🔴 LOS ANCHOS ESTÁN DECLARADOS PARA QUE LAS COLUMNAS NO SALTEN AL CARGAR (§3). `Nombre` es la
 * que absorbe el espacio libre; tiene que haber exactamente una así.
 *
 * ⚠️ `ancho` LLEVA TAMBIÉN LA ALINEACIÓN de las dos columnas numéricas/de acciones, y no es un
 * abuso del campo: `Columna.ancho` es el `className` del `<th>`, no un ancho literal. Poner el
 * `text-right` acá es lo que hace que el encabezado, el esqueleto y la fila real se alineen
 * IGUAL — si la alineación viviera sólo en la celda de datos, el título de la columna quedaría a
 * la izquierda de sus propios números.
 */
export const COLUMNAS: Columna[] = [
  { clave: "nombre", label: "Nombre", ancho: "" },
  { clave: "descripcion", label: "Descripción", ancho: "w-[30%]" },
  { clave: "responsable", label: "Responsable", ancho: "w-[18%]" },
  { clave: "colaboradores", label: "Colaboradores", ancho: "w-[13%] text-right" },
  // Editar y eliminar, 32px cada una más el aire. Sin texto en el encabezado: los dos íconos ya
  // dicen qué son y un "ACCIONES" de 10px sobre 88px se lee como ruido.
  { clave: "acciones", label: "", ancho: "w-[88px] text-right" },
]
