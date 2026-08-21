import type { Columna } from "@/components/ui/grillaTabla"
import type { EstadoVacante } from "@/types/vacantes"

/**
 * La grilla y el estado de `/vacantes`. Aparte de la tabla por lo mismo que `_grillaEmpleados` y
 * `_bajas`: es lo único que el encabezado, el esqueleto y las filas reales tienen que compartir
 * para que las columnas no se muevan entre un estado y el otro.
 *
 * 🔴 LOS ANCHOS ESTÁN DECLARADOS PARA QUE LAS COLUMNAS NO SALTEN AL CARGAR (§3). `Título` es la
 * que absorbe el espacio libre; tiene que haber exactamente una así.
 */
export const COLUMNAS: Columna[] = [
  { clave: "titulo", label: "Título", ancho: "" },
  { clave: "empresa", label: "Empresa", ancho: "w-[18%]" },
  { clave: "area", label: "Área", ancho: "w-[16%]" },
  { clave: "estado", label: "Estado", ancho: "w-[14%]" },
  { clave: "apertura", label: "Fecha de apertura", ancho: "w-[16%]" },
  // Solo el chevron al detalle: la fila entera ya navega, esto es la señal de que se puede.
  { clave: "acciones", label: "", ancho: "w-[48px]" },
]

/**
 * Los MISMOS textos que emite el export (`services/_vacantes_export.py::_ESTADO_LABEL`).
 * Si divergen, la pantalla y el archivo llaman distinto al mismo estado.
 */
export const ESTADO_LABEL: Record<EstadoVacante, string> = {
  nueva: "Nueva",
  en_proceso: "En proceso",
  con_candidatos: "Con candidatos",
  cerrada: "Cerrada",
}

/**
 * 🔴 NINGUNO ES AZUL, y ese es el cambio. `en_proceso` venía con `variant="default"`, o sea
 * `bg-primary`: un relleno azul en una celda de datos compitiendo con el ÚNICO relleno azul que
 * el patrón permite en la pantalla — el chip de filtro (§3). El estado es información semántica y
 * va con los pares de la paleta, medidos en los dos temas por `app/contrasteTokens.test.ts`.
 *
 * Los cuatro estados son un EMBUDO, y la semántica los sigue:
 *   · **nueva** → ATENCIÓN (`--warning`). Está abierta y todavía no se movió: es la que pide que
 *     alguien haga algo, y por eso es la única que se destaca en reposo.
 *   · **en proceso** → NEUTRO (`--secondary`). Está andando: no hay nada que decidir hoy.
 *   · **con candidatos** → ÉXITO. Es el avance real que esta pantalla mide — hay gente para
 *     entrevistar.
 *   · **cerrada** → PELIGRO, el mismo rojo tenue que ya tenía con `variant="destructive"`. Se
 *     conserva tal cual: no es un error, pero es la fila que sale del embudo y conviene que se
 *     lea distinta de las tres vivas.
 */
export const ESTADO_ESTILO: Record<EstadoVacante, string> = {
  nueva: "bg-warning-wash text-warning border-warning-line",
  en_proceso: "bg-secondary text-secondary-foreground border-border",
  con_candidatos: "bg-success-wash text-success border-success-line",
  cerrada: "bg-danger-wash text-destructive border-danger-line",
}
