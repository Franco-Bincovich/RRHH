import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla y los estados de `/eventos`. Aparte de la tabla por lo mismo que `_grillaEmpleados` y
 * `_bajas`: es lo único que el encabezado, el esqueleto y las filas reales tienen que compartir
 * para que las columnas no se muevan entre un estado y el otro.
 *
 * ⚠️ LA COLUMNA DE ACCIONES SE FILTRA POR `canWrite` EN EL CONSUMIDOR: sin permiso de escritura
 * no hay nada que resolver, editar ni borrar, y una columna vacía con su encabezado es una
 * promesa que la pantalla no cumple. Está fijado por `EventosTabla.test.tsx`.
 */
export const COLUMNAS: Columna[] = [
  { clave: "evento", label: "Recordatorio", ancho: "" },
  { clave: "fecha", label: "Fecha", ancho: "w-[12%]" },
  { clave: "aviso", label: "Aviso", ancho: "w-[12%]" },
  { clave: "visibilidad", label: "Visibilidad", ancho: "w-[13%]" },
  { clave: "estado", label: "Estado", ancho: "w-[18%]" },
  { clave: "acciones", label: "", ancho: "w-[128px] text-right" },
]

/**
 * 🔴 NINGUNO ES AZUL, y ese es el cambio. "Del equipo" venía con `variant="default"`, o sea
 * `bg-primary`: un relleno azul en una celda de datos compitiendo con el ÚNICO relleno azul que
 * el patrón permite en la pantalla — el chip de filtro (§3). Los pares salen de la paleta,
 * medidos en los dos temas por `app/contrasteTokens.test.ts`.
 *
 * 🔴 LA VISIBILIDAD NO ES UN EJE BUENO/MALO, así que ninguno de los dos lleva éxito ni peligro:
 * un evento del equipo y uno privado son igual de válidos. Lo que sí importa es que se
 * DISTINGAN de un vistazo, porque de eso depende quién lo ve en el dashboard:
 *   · **del equipo** → NEUTRO (`--secondary`), que es el default de la agenda.
 *   · **privado** → CONTORNO. Es el que sólo ve su autor, y el contorno lo separa sin gritar.
 */
export const VISIBILIDAD_ESTILO = {
  publica: "bg-secondary text-secondary-foreground border-border",
  privada: "",
} as const

/**
 * El estado del evento, que SÍ es un eje de progreso:
 *   · **resuelto** → ÉXITO. Se hizo lo que había que hacer y dejó de aparecer en el dashboard.
 *   · **pendiente** → ATENCIÓN. Es lo que la agenda existe para mostrar; en reposo tiene que
 *     poder leerse sin buscarlo.
 */
export const ESTADO_ESTILO = {
  resuelto: "bg-success-wash text-success border-success-line",
  pendiente: "bg-warning-wash text-warning border-warning-line",
} as const
