import type { Columna } from "@/components/ui/grillaTabla"
import type { EstadoVacacion } from "@/types/vacaciones"

/**
 * La grilla y el estado de `/vacaciones` (vista lista). Aparte de la tabla por lo mismo que
 * `_grillaEmpleados` y `_bajas`: es lo único que el encabezado, el esqueleto y las filas reales
 * tienen que compartir para que las columnas no se muevan entre un estado y el otro.
 *
 * 🔴 LOS ANCHOS ESTÁN DECLARADOS PARA QUE LAS COLUMNAS NO SALTEN AL CARGAR (§3). `Colaborador` es
 * la que absorbe el espacio libre; tiene que haber exactamente una así.
 */
export const COLUMNAS: Columna[] = [
  { clave: "colaborador", label: "Colaborador", ancho: "" },
  { clave: "area", label: "Área", ancho: "w-[14%]" },
  { clave: "empresa", label: "Empresa", ancho: "w-[14%]" },
  { clave: "desde", label: "Desde", ancho: "w-[11%]" },
  { clave: "hasta", label: "Hasta", ancho: "w-[11%]" },
  { clave: "dias", label: "Días", ancho: "w-[7%]" },
  { clave: "estado", label: "Estado", ancho: "w-[12%]" },
  // Los documentos (32px) y "Cancelar" (texto). Sin encabezado: el ícono y la palabra ya dicen
  // qué son, y un "ACCIONES" en mayúsculas de 10px sobre ellos se lee como ruido.
  { clave: "acciones", label: "", ancho: "w-[150px]" },
]

export const ESTADO_LABEL: Record<EstadoVacacion, string> = {
  planificada: "Planificada",
  tomada: "Tomada",
  cancelada: "Cancelada",
}

/**
 * 🔴 NINGUNO ES AZUL, y ese es el cambio. `planificada` venía con `variant="default"`, o sea
 * `bg-primary`: un relleno azul en una celda de datos, repetido en veinte filas, compitiendo con
 * el ÚNICO relleno azul que el patrón permite en la pantalla — el chip de filtro (§3). El estado
 * es información semántica y va con los pares de la paleta, medidos en los dos temas por
 * `app/contrasteTokens.test.ts`.
 *
 * Qué semántica le toca a cada uno, y por qué:
 *   · **planificada** → NEUTRO (`--secondary`). Todavía no pasó: no es un logro ni un problema,
 *     es una fecha reservada. Pintarla de verde diría "listo" sobre algo que no ocurrió.
 *   · **tomada** → ÉXITO. Es el único de los tres que está cerrado y salió bien: el descanso se
 *     usó y esos días ya no cuentan como saldo.
 *   · **cancelada** → PELIGRO, el mismo rojo tenue que ya tenía con `variant="destructive"`. No
 *     es un error del sistema, pero sí la fila que hay que mirar cuando el saldo no cierra.
 */
export const ESTADO_ESTILO: Record<EstadoVacacion, string> = {
  planificada: "bg-secondary text-secondary-foreground border-border",
  tomada: "bg-success-wash text-success border-success-line",
  cancelada: "bg-danger-wash text-destructive border-danger-line",
}
