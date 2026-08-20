import type { Empleado } from "@/types/empleado"

/**
 * Cómo se ve y cómo se dice el estado de un legajo. **Un solo lugar**: hasta esta tanda había
 * tres formas distintas del mismo dato —el mapa tipado de `DatosEmpleadoSection`, el
 * `Record<string, …>` de `EmpleadosTable` y el texto crudo del panel laboral— y las tres se
 * mantenían a mano.
 *
 * 🔑 EL TIPO SE ATA A `Empleado["estado"]` A PROPÓSITO, y ahí está todo el valor.
 * Un `Record<string, …>` compila con cualquier clave: un typo no lo caza nadie, y cuando la
 * unión se ensanchó (migración 120: `preingreso` y `suspendido`) el mapa suelto no dijo nada.
 * El tipado sí, y **ese rojo es la feature, no la molestia**.
 *
 * ⚠️ `Partial` Y NO `Record` COMPLETO: `suspendido` cae DELIBERADAMENTE al default de abajo, no
 * es una entrada olvidada. Es un valor muerto —está en el CHECK pero ningún camino del backend lo
 * escribe, ver `utils/estados_empleado.py`— y darle un estilo propio sería decidir cómo se ve algo
 * que nadie produce. El día que algo lo escriba, se le elige uno acá.
 *
 * 🔴 NINGUNO ES AZUL. El chip de estado vive en la barra de identidad, al lado del botón primario:
 * un relleno `--primary` ahí compite con la acción y la pantalla pasa a tener dos cosas gritando.
 * El estado es información semántica y va con los pares de la paleta (`--success-*`, `--warning-*`,
 * `--danger-*`), medidos a 4,73:1 o mejor en los dos temas (`app/contrasteTokens.test.ts`).
 */
export const ESTADO_LABEL: Partial<Record<Empleado["estado"], string>> = {
  activo: "Activo",
  preingreso: "Preingreso",
  baja: "Baja",
  licencia: "Licencia",
}

export const ESTADO_ESTILO: Partial<Record<Empleado["estado"], string>> = {
  activo: "bg-success-wash text-success border-success-line",
  // Preingreso es "todavía no entró": no es un estado bueno ni malo, es uno que pide atención.
  preingreso: "bg-warning-wash text-warning border-warning-line",
  licencia: "bg-secondary text-secondary-foreground border-border",
  baja: "bg-danger-wash text-destructive border-danger-line",
}

/** El texto del chip. Un estado sin entrada se muestra crudo antes que en blanco. */
export function etiquetaEstado(estado: Empleado["estado"]): string {
  return ESTADO_LABEL[estado] ?? estado
}
