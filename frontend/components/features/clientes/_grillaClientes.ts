import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla y el estado de `/clientes`. Aparte de la tabla por lo mismo que `_grillaEmpleados` y
 * `_bajas`: es lo único que el encabezado, el esqueleto y las filas reales tienen que compartir
 * para que las columnas no se muevan entre un estado y el otro.
 *
 * ⚠️ LA COLUMNA DE ACCIONES SE FILTRA POR `canWrite` EN EL CONSUMIDOR, no acá: sin permiso de
 * escritura no hay ninguna acción de fila y una columna vacía con su encabezado sería una
 * promesa que la pantalla no cumple. Está fijado por `ClientesTabla.test.tsx`.
 */
export const COLUMNAS: Columna[] = [
  { clave: "cliente", label: "Cliente", ancho: "" },
  { clave: "estado", label: "Estado", ancho: "w-[22%]" },
  { clave: "acciones", label: "", ancho: "w-[88px] text-right" },
]

/**
 * 🔴 NINGUNO ES AZUL, y ese es el cambio. "Activo" venía con `variant="default"`, o sea
 * `bg-primary`: un relleno azul en una celda de datos, repetido en todas las filas, compitiendo
 * con el ÚNICO relleno azul que el patrón permite en la pantalla — el chip de filtro (§3). El
 * estado es información semántica y va con los pares de la paleta, medidos en los dos temas por
 * `app/contrasteTokens.test.ts`.
 *
 * Qué semántica le toca a cada uno:
 *   · **activo** → ÉXITO. Es el estado utilizable: aparece en el link público de carga de horas.
 *     Es lo que el operador viene a confirmar cuando alguien reporta que "no le sale el cliente".
 *   · **dado de baja** → NEUTRO (`--secondary`). La baja es LÓGICA y reversible: las horas ya
 *     cargadas contra él siguen ahí y se puede reactivar desde el modal. Pintarlo de rojo lo
 *     leería como un borrado o como un error, y no es ninguna de las dos cosas.
 */
export const ESTADO_ESTILO = {
  activo: "bg-success-wash text-success border-success-line",
  baja: "bg-secondary text-secondary-foreground border-border",
} as const
