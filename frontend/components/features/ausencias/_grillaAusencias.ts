import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla de `/ausencias`. Aparte de la tabla por lo mismo que `_grillaEmpleados` y `_bajas`:
 * es lo único que el encabezado, el esqueleto y las filas reales tienen que compartir para que
 * las columnas no se muevan entre un estado y el otro.
 *
 * 🔴 LOS ANCHOS ESTÁN DECLARADOS PARA QUE LAS COLUMNAS NO SALTEN AL CARGAR (§3). Esta tabla es la
 * más ancha del bloque —diez columnas— y es justamente donde más se nota: sin anchos, el esqueleto
 * reparte el ancho en partes iguales y al llegar los datos "Días" se achica, "Motivo" se estira y
 * la fila entera se reacomoda de golpe.
 * `Colaborador` es la que absorbe el espacio libre; tiene que haber exactamente una así.
 *
 * ⚠️ `Empresa` se filtra afuera cuando el sidebar tiene una empresa elegida (mismo criterio que
 * empleados y bajas): con una sola empresa a la vista, la columna repetiría el mismo texto en
 * todas las filas.
 */
export const COLUMNAS: Columna[] = [
  { clave: "colaborador", label: "Colaborador", ancho: "" },
  { clave: "area", label: "Área", ancho: "w-[11%]" },
  { clave: "empresa", label: "Empresa", ancho: "w-[11%]" },
  { clave: "tipo", label: "Tipo", ancho: "w-[12%]" },
  { clave: "desde", label: "Desde", ancho: "w-[9%]" },
  { clave: "hasta", label: "Hasta", ancho: "w-[9%]" },
  { clave: "dias", label: "Días", ancho: "w-[6%]" },
  { clave: "justificada", label: "Justificada", ancho: "w-[9%]" },
  { clave: "motivo", label: "Motivo", ancho: "w-[14%]" },
  // Tres acciones (documentos, editar, eliminar) de 32px cada una más el aire entre ellas.
  { clave: "acciones", label: "", ancho: "w-[120px]" },
]
