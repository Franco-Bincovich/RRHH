import type { Columna } from "@/components/ui/grillaTabla"
import type { EstadoObjetivo, PrioridadObjetivo } from "@/types/objetivo"

/**
 * La grilla y los estados de la vista Lista de `/objetivos`. Aparte de la tabla por lo mismo que
 * `_grillaEmpleados` y `_bajas`: es lo único que el encabezado, el esqueleto y las filas reales
 * tienen que compartir para que las columnas no se muevan entre un estado y el otro.
 *
 * ⚠️ La columna de acciones se filtra por `canWrite` en el consumidor: sin permiso no hay nada que
 * editar ni borrar, y una columna vacía con su encabezado es una promesa que la pantalla no cumple.
 */
export const COLUMNAS: Columna[] = [
  { clave: "titulo", label: "Título", ancho: "" },
  { clave: "responsable", label: "Responsable", ancho: "w-[16%]" },
  { clave: "prioridad", label: "Prioridad", ancho: "w-[10%]" },
  { clave: "estado", label: "Estado", ancho: "w-[11%]" },
  { clave: "empresa", label: "Empresa", ancho: "w-[12%]" },
  { clave: "entrega", label: "Fecha entrega", ancho: "w-[12%]" },
  { clave: "acciones", label: "", ancho: "w-[88px] text-right" },
]

export const ESTADO_LABEL: Record<EstadoObjetivo, string> = {
  por_hacer: "Por hacer",
  haciendo: "Haciendo",
  terminado: "Terminado",
}

/**
 * 🔴 NINGUNO ES AZUL, y ese es el cambio. `haciendo` venía con `variant="default"`, o sea
 * `bg-primary`: un relleno azul en una celda de datos compitiendo con el ÚNICO relleno azul que el
 * patrón permite en la pantalla — el chip de filtro (§3). Los pares salen de la paleta, medidos en
 * los dos temas por `app/contrasteTokens.test.ts`.
 *
 * 🔴 SON TRES ESTADOS, NO UN PORCENTAJE. `docs/SISTEMA-DE-DISENO.md` §7 es explícito: en objetivos
 * **no hay avance en %**, hay estado. Ninguna de estas tres etiquetas puede insinuar una fracción
 * ("50% completado", "a mitad de camino") porque el dato no existe y nadie lo carga.
 *   · **por hacer** → CONTORNO. Todavía no arrancó: no es un problema, es la cola.
 *   · **haciendo** → ATENCIÓN. Es lo que está abierto ahora, y es lo que un tablero existe para
 *     que se vea de un vistazo.
 *   · **terminado** → ÉXITO. Cerró.
 */
export const ESTADO_ESTILO: Record<EstadoObjetivo, string> = {
  por_hacer: "",
  haciendo: "bg-warning-wash text-warning border-warning-line",
  terminado: "bg-success-wash text-success border-success-line",
}

export const PRIORIDAD_LABEL: Record<PrioridadObjetivo, string> = {
  baja: "Baja", media: "Media", alta: "Alta",
}

/**
 * 🔴 "MEDIA" DEJÓ DE PINTARSE CON `--primary`. Venía con `border-primary/40 bg-primary/10
 * text-primary`: no era un `variant="default"` sólido, pero era el color de la MARCA usado como
 * dato, en la misma pantalla donde el chip de filtro es el único que puede llevarlo. La escala
 * pasa a ser la de la paleta y se lee como lo que es — una escala de tres pasos:
 * neutro · atención · peligro.
 */
export const PRIORIDAD_ESTILO: Record<PrioridadObjetivo, string> = {
  baja: "border-border bg-transparent text-muted-foreground",
  media: "bg-warning-wash text-warning border-warning-line",
  alta: "bg-danger-wash text-destructive border-danger-line",
}
