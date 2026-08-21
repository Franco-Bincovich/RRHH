import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla de `/auditoria`. Aparte de la tabla por lo mismo que `_grillaEmpleados` y `_bajas`:
 * es lo único que el encabezado, el esqueleto y las filas reales tienen que compartir para que
 * las columnas no se muevan entre un estado y el otro.
 *
 * 🔴 LOS ANCHOS ESTÁN DECLARADOS PARA QUE LAS COLUMNAS NO SALTEN AL CARGAR (§3). `Detalle` es la
 * que absorbe el espacio libre —y es la que más lo necesita: el resumen del diff es texto de
 * largo impredecible—; tiene que haber exactamente una así.
 *
 * ⚠️ NO HAY COLUMNA DE ACCIONES SEPARADA. "Ver detalle" vive DENTRO de la celda de Detalle, al
 * lado del resumen que amplía, y ahí es donde se entiende qué abre. Una columna propia lo
 * separaría del texto al que se refiere.
 */
export const COLUMNAS: Columna[] = [
  { clave: "fecha", label: "Fecha", ancho: "w-[13%]" },
  { clave: "usuario", label: "Usuario", ancho: "w-[13%]" },
  { clave: "empresa", label: "Empresa", ancho: "w-[12%]" },
  { clave: "entidad", label: "Sección", ancho: "w-[11%]" },
  { clave: "evento", label: "Evento", ancho: "w-[16%]" },
  { clave: "accion", label: "Acción", ancho: "w-[9%]" },
  { clave: "detalle", label: "Detalle", ancho: "" },
]
