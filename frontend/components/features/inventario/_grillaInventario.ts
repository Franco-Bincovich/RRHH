import type { Columna } from "@/components/ui/grillaTabla"

/**
 * Las grillas y los estados de las DOS pestañas de `/inventario`. Un solo archivo para las dos
 * porque comparten el vocabulario (ítem, tipo, número de serie, empresa) y separarlas dejaría
 * dos archivos de quince líneas que se leen juntos igual.
 *
 * 🔴 LOS ANCHOS ESTÁN DECLARADOS PARA QUE LAS COLUMNAS NO SALTEN AL CARGAR (§3). En cada lista
 * hay exactamente UNA columna sin ancho, que es la que absorbe el espacio libre.
 *
 * ⚠️ `Empresa` se filtra afuera cuando el sidebar tiene una empresa elegida, y la columna de
 * acciones de asignaciones se filtra por `canWrite`: sin permiso no hay nada que devolver, y una
 * columna vacía con su encabezado es una promesa que la pantalla no cumple.
 */
export const COLUMNAS_ITEMS: Columna[] = [
  { clave: "nombre", label: "Nombre", ancho: "" },
  { clave: "tipo", label: "Tipo", ancho: "w-[11%]" },
  { clave: "serie", label: "N° Serie", ancho: "w-[12%]" },
  { clave: "estado", label: "Estado", ancho: "w-[11%]" },
  { clave: "empresa", label: "Empresa", ancho: "w-[11%]" },
  { clave: "asignado", label: "Asignado a", ancho: "w-[14%]" },
  { clave: "alta", label: "Alta", ancho: "w-[9%]" },
  // Historial (siempre), editar y eliminar (sólo con permiso). Va siempre: el historial es una
  // LECTURA y la tiene cualquiera que llegue a esta pestaña.
  { clave: "acciones", label: "", ancho: "w-[120px]" },
]

export const COLUMNAS_ASIGNACIONES: Columna[] = [
  { clave: "colaborador", label: "Colaborador", ancho: "" },
  { clave: "item", label: "Ítem", ancho: "w-[18%]" },
  { clave: "tipo", label: "Tipo", ancho: "w-[12%]" },
  { clave: "serie", label: "N° Serie", ancho: "w-[13%]" },
  { clave: "empresa", label: "Empresa", ancho: "w-[13%]" },
  { clave: "desde", label: "Desde", ancho: "w-[10%]" },
  { clave: "acciones", label: "", ancho: "w-[112px] text-right" },
]

export const ESTADO_ITEM_LABEL: Record<string, string> = {
  disponible: "Disponible",
  asignado: "Asignado",
  en_reparacion: "En reparación",
  baja: "Baja",
}

/**
 * 🔴 NINGUNO ES AZUL, y ese es el cambio. `disponible` venía con `variant="default"`, o sea
 * `bg-primary`: un relleno azul en una celda de datos, repetido en las filas de un catálogo
 * entero, compitiendo con el ÚNICO relleno azul que el patrón permite en la pantalla — el chip de
 * filtro (§3). Los pares salen de la paleta, medidos en los dos temas por
 * `app/contrasteTokens.test.ts`.
 *
 * Los cuatro estados son el ciclo de vida de un activo y la semántica lo sigue:
 *   · **disponible** → ÉXITO. Es el que se puede asignar hoy: lo que esta pantalla contesta
 *     cuando entra alguien nuevo.
 *   · **asignado** → NEUTRO. Está en uso y todo está bien; no hay nada que decidir.
 *   · **en reparación** → ATENCIÓN. Está fuera de circulación y alguien lo tiene que seguir.
 *   · **baja** → PELIGRO, el mismo rojo tenue que ya tenía con `variant="destructive"`. Salió del
 *     inventario y no vuelve.
 */
export const ESTADO_ITEM_ESTILO: Record<string, string> = {
  disponible: "bg-success-wash text-success border-success-line",
  asignado: "bg-secondary text-secondary-foreground border-border",
  en_reparacion: "bg-warning-wash text-warning border-warning-line",
  baja: "bg-danger-wash text-destructive border-danger-line",
}
