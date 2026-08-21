"use client"

import { useState } from "react"
import { toast } from "sonner"

import { ApiError } from "@/services/api"
import { activarEmpleado } from "@/services/empleados"
import type { Empleado } from "@/types/empleado"

/**
 * "Confirmar ingreso": el acto que pasa un legajo de `preingreso` a `activo`, sin su botón.
 *
 * 🔴 POR QUÉ ES UN HOOK Y NO SIGUE ADENTRO DE `ActivarEmpleadoButton`. El acto tiene DOS puntos
 * de entrada —la ficha del empleado y la fila de `/proximos-ingresos`— y los dos botones no
 * pueden ser el mismo componente: el de la ficha es la acción principal de la pantalla (grande,
 * con ícono y `min-h-11`) y el de la fila convive con otras 5 columnas en 46px de alto. Lo que
 * SÍ tiene que ser el mismo es esto: la llamada, el toast de éxito y —sobre todo— el manejo del
 * error. Dos copias divergen en el primer cambio, y la que quede vieja va a ser justo la que
 * traduzca el mensaje del backend a un genérico.
 *
 * 🔴 EL MENSAJE DEL BACKEND SE MUESTRA TAL CUAL, sin traducir ni resumir. `INGRESO_AUN_NO_OCURRIO`
 * ya dice la fecha que falta y qué hacer si la persona entró antes de lo previsto ("corregí la
 * fecha en el legajo y después activala"). Reemplazarlo por "no se pudo activar" deja al usuario
 * sin la única información que resuelve el caso — que es además el único error de los tres que
 * se puede encontrar operando normal: el 404 y el 409 exigen un id ajeno o una carrera entre dos
 * pestañas. El fallback genérico es SOLO para lo que no es un `ApiError` (la red caída), que no
 * trae ningún mensaje que valga la pena mostrar.
 *
 * ⚠️ El estado es el ID de quien se está activando, no un booleano: en una tabla hay N filas con
 * su botón, y un `activando: boolean` los deshabilitaría a todos al tocar uno solo.
 */
export type PersonaActivable = Pick<Empleado, "id" | "nombre" | "apellido">

/**
 * El acto en sí, SIN React: llamar, avisar y traducir el error.
 *
 * 🔑 ESTÁ SEPARADO DEL HOOK PARA PODER PROBARLO. vitest corre sin jsdom: un hook no se puede
 * ejecutar fuera de un render, y un render a string no dispara handlers. Con la lógica adentro
 * del hook, "el mensaje del backend se muestra tal cual" no era verificable por ningún test — y
 * es exactamente la línea que un refactor apurado reemplaza por un genérico. Lo que queda en el
 * hook es el flag de "en vuelo", que sí es estado de React.
 *
 * 🔴 `onActivado` SE LLAMA SOLO SI LA LLAMADA SALIÓ BIEN, y del lado de la pantalla es el
 * `recargar` del listado: por eso la fila desaparece de /proximos-ingresos sin sacarla del array
 * a mano. Se recarga en vez de filtrar en el cliente porque el total del encabezado y la
 * paginación los cuenta el backend; un borrado local dejaría el número diciendo uno de más.
 */
export async function confirmarIngreso(
  empleado: PersonaActivable, onActivado: () => void,
): Promise<void> {
  try {
    await activarEmpleado(empleado.id)
    toast.success(`${empleado.nombre} ${empleado.apellido} ya figura como activo`)
    onActivado()
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : "No se pudo confirmar el ingreso.")
  }
}

export function useActivarEmpleado(onActivado: () => void) {
  const [activandoId, setActivandoId] = useState<string | null>(null)

  async function activar(empleado: PersonaActivable) {
    setActivandoId(empleado.id)
    try {
      await confirmarIngreso(empleado, onActivado)
    } finally {
      setActivandoId(null)
    }
  }

  return { activandoId, activar }
}
