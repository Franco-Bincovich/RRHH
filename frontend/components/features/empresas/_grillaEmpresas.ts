import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla y el estado de `/empresas`. Aparte de la tabla por lo mismo que `_grillaEmpleados` y
 * `_bajas`: es lo único que el encabezado, el esqueleto y las filas reales tienen que compartir
 * para que las columnas no se muevan entre un estado y el otro.
 *
 * 🔴 LA COLUMNA DE ACCIONES VA SIEMPRE, incluso sin permiso de escritura, y eso la diferencia de
 * áreas y clientes: acá queda el chevron al detalle de la empresa, que es una LECTURA y la tiene
 * cualquiera que llegue a esta pantalla. Editar y el toggle de activa sí se omiten sin `canWrite`.
 */
export const COLUMNAS: Columna[] = [
  { clave: "nombre", label: "Nombre", ancho: "" },
  { clave: "cuit", label: "CUIT", ancho: "w-[16%]" },
  { clave: "email", label: "Email", ancho: "w-[24%]" },
  { clave: "estado", label: "Estado", ancho: "w-[12%]" },
  { clave: "acciones", label: "", ancho: "w-[128px] text-right" },
]

/**
 * 🔴 NINGUNO ES AZUL, y ese es el cambio. "Activa" venía con `variant="default"`, o sea
 * `bg-primary`: un relleno azul en una celda de datos compitiendo con el ÚNICO relleno azul que
 * el patrón permite en la pantalla — el chip de filtro (§3). Los pares salen de la paleta,
 * medidos en los dos temas por `app/contrasteTokens.test.ts`.
 *
 * Qué semántica le toca a cada uno:
 *   · **activa** → ÉXITO. Es la que aparece en el selector del sidebar de todo el equipo y la que
 *     se puede elegir al dar de alta cualquier cosa. Es el estado operable.
 *   · **inactiva** → NEUTRO (`--secondary`). No es un error ni una baja: la empresa sigue
 *     existiendo con todos sus datos y el toggle la devuelve. Pintarla de rojo la leería como
 *     borrada.
 */
export const ESTADO_ESTILO = {
  activa: "bg-success-wash text-success border-success-line",
  inactiva: "bg-secondary text-secondary-foreground border-border",
} as const
