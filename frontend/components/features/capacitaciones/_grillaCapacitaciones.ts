import type { Columna } from "@/components/ui/grillaTabla"

/**
 * Las grillas y los estados de las DOS pestañas de `/capacitaciones` (Formación). Un solo archivo
 * para las dos porque comparten vocabulario y se leen juntas.
 *
 * 🔴 LOS ANCHOS ESTÁN DECLARADOS PARA QUE LAS COLUMNAS NO SALTEN AL CARGAR (§3). En cada lista hay
 * exactamente UNA columna sin ancho, que es la que absorbe el espacio libre.
 */
export const COLUMNAS_CATALOGO: Columna[] = [
  { clave: "nombre", label: "Nombre", ancho: "" },
  { clave: "categoria", label: "Categoría", ancho: "w-[15%]" },
  { clave: "duracion", label: "Duración", ancho: "w-[10%]" },
  { clave: "empresa", label: "Empresa", ancho: "w-[14%]" },
  { clave: "obligatoria", label: "Obligatoria", ancho: "w-[11%]" },
  { clave: "estado", label: "Estado", ancho: "w-[10%]" },
  { clave: "acciones", label: "", ancho: "w-[88px] text-right" },
]

export const COLUMNAS_ASIGNACIONES: Columna[] = [
  { clave: "colaborador", label: "Colaborador", ancho: "" },
  { clave: "formacion", label: "Formación", ancho: "w-[18%]" },
  { clave: "estado", label: "Estado", ancho: "w-[10%]" },
  { clave: "empresa", label: "Empresa", ancho: "w-[11%]" },
  { clave: "limite", label: "Fecha límite", ancho: "w-[10%]" },
  { clave: "completado", label: "Completado", ancho: "w-[10%]" },
  { clave: "certificado", label: "Certificado", ancho: "w-[11%]" },
  { clave: "acciones", label: "", ancho: "w-[88px] text-right" },
]

/**
 * 🔴 NINGUNO ES AZUL, y ese es el cambio. En el catálogo, "Obligatoria: Sí" venía con
 * `variant="default"` —`bg-primary`— y en asignaciones lo mismo pasaba con "Completado": relleno
 * azul en celdas de datos, compitiendo con el ÚNICO relleno azul que el patrón permite en la
 * pantalla, que es el chip de filtro (§3). Los pares salen de la paleta, medidos en los dos temas
 * por `app/contrasteTokens.test.ts`.
 *
 * ⚠️ "OBLIGATORIA" VA CON EL PAR DE ATENCIÓN Y NO CON EL DE ÉXITO, y conviene leer por qué: que un
 * curso sea obligatorio no es un logro, es una CONDICIÓN que genera trabajo — hay que asignarlo a
 * todo el mundo y perseguir a quien no lo completó. El ámbar es la señal de "esto pide acción", y
 * es exactamente lo que significa. "No obligatoria" queda en contorno: es la ausencia de esa
 * condición, no un estado propio.
 */
export const OBLIGATORIA_ESTILO = {
  si: "bg-warning-wash text-warning border-warning-line",
  no: "",
} as const

/** El curso dado de baja del catálogo sigue existiendo (baja lógica): neutro, no rojo. */
export const ACTIVO_ESTILO = {
  activo: "bg-success-wash text-success border-success-line",
  inactivo: "bg-secondary text-secondary-foreground border-border",
} as const

export const ESTADO_ASIGNACION_LABEL: Record<string, string> = {
  pendiente: "Pendiente",
  en_curso: "En curso",
  completado: "Completado",
}

/**
 * El estado de una asignación es un progreso de tres pasos y la semántica lo sigue:
 *   · **pendiente** → ATENCIÓN. Es la fila que la pantalla existe para encontrar.
 *   · **en curso** → NEUTRO. Está pasando y no hay nada que decidir hoy.
 *   · **completado** → ÉXITO. Cerró, y con certificado si lo pedía.
 */
export const ESTADO_ASIGNACION_ESTILO: Record<string, string> = {
  pendiente: "bg-warning-wash text-warning border-warning-line",
  en_curso: "bg-secondary text-secondary-foreground border-border",
  completado: "bg-success-wash text-success border-success-line",
}
