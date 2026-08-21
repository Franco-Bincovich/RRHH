import type { Columna } from "@/components/ui/grillaTabla"

/**
 * Las dos grillas de /assessment —campañas y resultados— y los mapas de estilo semántico de sus
 * etiquetas. Sin JSX: lo importan las dos tablas y podría importarlo un test sin montar nada.
 *
 * 🔴 LA COLUMNA DE EMPRESA SE FILTRA EN LA TABLA, no acá: existe sólo con el sidebar en
 * consolidado. Está en la lista con su ancho para que, cuando aparezca, no se recalculen los
 * anchos de las demás.
 */

export const COLUMNAS_CAMPANAS: readonly Columna[] = [
  { clave: "nombre", label: "Nombre", ancho: "" },
  { clave: "empresa", label: "Empresa", ancho: "w-[14%]" },
  { clave: "tipo", label: "Tipo", ancho: "w-[11%]" },
  { clave: "creada", label: "Creada", ancho: "w-[11%]" },
  { clave: "links", label: "Links", ancho: "w-[9%] text-right" },
  { clave: "completados", label: "Completados", ancho: "w-[13%] text-right" },
  { clave: "estado", label: "Estado", ancho: "w-[11%]" },
]

export const COLUMNAS_RESULTADOS: readonly Columna[] = [
  { clave: "evaluado", label: "Evaluado", ancho: "" },
  { clave: "empresa", label: "Empresa", ancho: "w-[14%]" },
  { clave: "tipo", label: "Tipo", ancho: "w-[11%]" },
  { clave: "fecha", label: "Fecha", ancho: "w-[11%]" },
  { clave: "perfil", label: "Perfil dominante", ancho: "w-[18%]" },
  { clave: "score", label: "Score", ancho: "w-[9%] text-right" },
]

export const TIPO_LABEL: Record<string, string> = {
  completo:   "Completo",
  conductual: "Conductual",
  cognitivo:  "Cognitivo",
}

/*
 * 🔴 EL ESTADO DEJÓ DE SER `variant="default"`, QUE ES EL RELLENO `bg-primary`.
 *
 * Había un `ESTADO_VARIANT` que pintaba "activa" con el color de la marca y todo lo demás con
 * `secondary`. Dos problemas, ninguno estético:
 *   · `bg-primary` está reservado para el chip de filtro activo y para la acción principal de la
 *     pantalla. Una etiqueta que se repite en cada fila con ese color le roba el énfasis a lo
 *     único accionable que hay arriba.
 *   · "cerrada", "borrador" y "archivada" caían todas en el MISMO gris, así que tres estados que
 *     significan cosas distintas —terminó bien, todavía no salió, ya no se usa— se leían igual.
 *
 * Ahora cada uno sale de la paleta semántica: en curso es `warning` (algo está esperando a que
 * alguien responda), cerrada es `success` (llegó a destino), borrador queda neutro y archivada
 * queda apagada. `""` = el contorno pelado de `variant="outline"`, sin color.
 */
export const ESTADO_ESTILO: Record<string, string> = {
  activa:    "border-warning-line bg-warning-wash text-warning",
  cerrada:   "border-success-line bg-success-wash text-success",
  borrador:  "",
  archivada: "text-muted-foreground",
}

export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
}
