import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla y el estado de `/periodos`. Aparte de la tabla por lo mismo que `_grillaEmpleados` y
 * `_bajas`: es lo único que el encabezado, el esqueleto y las filas reales tienen que compartir
 * para que las columnas no se muevan entre un estado y el otro.
 *
 * ⚠️ LA COLUMNA DE ACCIONES SE FILTRA POR `canWrite` EN EL CONSUMIDOR: sin permiso de escritura
 * no hay nada que reabrir, y una columna vacía con su encabezado es una promesa que la pantalla
 * no cumple. Es el mismo criterio que en áreas y clientes.
 */
export const COLUMNAS: Columna[] = [
  { clave: "modulo", label: "Módulo", ancho: "" },
  { clave: "desde", label: "Desde", ancho: "w-[11%]" },
  { clave: "hasta", label: "Hasta", ancho: "w-[11%]" },
  { clave: "estado", label: "Estado", ancho: "w-[12%]" },
  { clave: "detalle", label: "Detalle", ancho: "w-[28%]" },
  { clave: "acciones", label: "", ancho: "w-[120px] text-right" },
]

/**
 * 🔴 NINGUNO ES AZUL, y ese es el cambio. "Cerrado" venía con `variant="default"`, o sea
 * `bg-primary`: un relleno azul en una celda de datos compitiendo con el ÚNICO relleno azul que
 * el patrón permite en la pantalla — el chip de filtro (§3). Los pares salen de la paleta,
 * medidos en los dos temas por `app/contrasteTokens.test.ts`.
 *
 * 🔴 Y LA SEMÁNTICA ACÁ ES AL REVÉS DE LO QUE PARECE, así que conviene leerla antes de "corregirla":
 *   · **cerrado** → ÉXITO. Suena a "terminado" y es lo contrario: es el CONTROL PUESTO. Un
 *     período cerrado es el que nadie puede editar por accidente, que es exactamente lo que esta
 *     pantalla existe para conseguir. Es el estado deseado.
 *   · **reabierto** → ATENCIÓN (`--warning`). Es la excepción: alguien levantó el bloqueo y, hasta
 *     que se vuelva a cerrar, ese rango se puede tocar. No es un error —por eso no es rojo— pero
 *     es la fila que hay que mirar cuando un número del mes cambia sin que nadie sepa por qué.
 */
export const ESTADO_ESTILO = {
  cerrado: "bg-success-wash text-success border-success-line",
  reabierto: "bg-warning-wash text-warning border-warning-line",
} as const
