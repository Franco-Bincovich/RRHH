/**
 * La GRILLA de la tabla de empleados: qué columnas hay y cuánto miden.
 *
 * ⚠️ `Encabezado` y `FilasEsqueleto` VIVÍAN ACÁ y se mudaron a `components/ui/grillaTabla.tsx` al
 * aparecer la segunda y la tercera tabla del patrón (`/proximos-ingresos` y `/bajas`): ninguna de
 * las dos sabía nada de empleados. Se RE-EXPORTAN desde acá para que `EmpleadosTable` —y
 * cualquier import existente— siga apuntando al mismo lugar; el corte fue de dónde vive el
 * código, no de quién lo usa.
 *
 * Lo que se queda es `COLUMNAS`, que es lo único propio de esta pantalla, y el motivo por el que
 * el archivo existía: acá está TODO lo que el encabezado, el esqueleto y las filas reales tienen
 * que compartir para que las columnas no se muevan entre un estado y el otro.
 */
import { type Columna, Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"

export { Encabezado, FilasEsqueleto }

/**
 * 🔴 LOS ANCHOS ESTÁN DECLARADOS PARA QUE LAS COLUMNAS NO SALTEN AL CARGAR (§3), y por eso viven
 * en UNA lista que usan el encabezado, el esqueleto y las filas reales. Si el esqueleto declarara
 * los suyos, las columnas se acomodarían solas al llegar los datos y la pantalla saltaría — que es
 * exactamente lo que el esqueleto viene a evitar.
 * `Nombre` no lleva ancho: es la columna que absorbe el espacio libre.
 */
export const COLUMNAS: Columna[] = [
  { clave: "nombre", label: "Nombre", ancho: "" },
  { clave: "empresa", label: "Empresa", ancho: "w-[16%]" },
  { clave: "area", label: "Área", ancho: "w-[14%]" },
  { clave: "roles", label: "Roles", ancho: "w-[20%]" },
  { clave: "modalidad", label: "Modalidad", ancho: "w-[12%]" },
  { clave: "estado", label: "Estado", ancho: "w-[10%]" },
  // La columna de acciones no lleva texto en el encabezado: el ícono de cada fila ya dice qué es,
  // y un "Acciones" en mayúsculas de 10px sobre una columna de 40px se lee como ruido.
  { clave: "acciones", label: "", ancho: "w-[48px]" },
]
